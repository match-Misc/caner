import argparse
import logging
import os
import sys
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from dotenv import load_dotenv
from flask import Flask
from tqdm import tqdm

from meal_translation import (
    get_meal_translation_request_delay_seconds,
    has_configured_translation_api_key,
    translate_meal_batch,
)
from models import Meal, db
from mps_scoring import MPSAuthenticationError
from schema import ensure_application_schema


logger = logging.getLogger("fetch_meal_translations")
DEFAULT_WORKERS = 2
DEFAULT_BATCH_SIZE = 20


def configure_logging():
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)
    logger.propagate = False


def load_environment():
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info("Loaded environment variables from %s", dotenv_path)
    else:
        logger.warning(
            ".env file not found at %s. Assuming environment variables are set externally.",
            dotenv_path,
        )


def create_app():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("Database configuration missing. Please ensure DATABASE_URL is set.")
        return None

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 300
    db.init_app(app)
    return app


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch English meal translations using the configured OpenRouter model."
    )
    parser.add_argument(
        "--overwrite-all",
        action="store_true",
        help="Recalculate and overwrite English translations for all meals.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(
            os.environ.get("MEAL_TRANSLATION_BATCH_SIZE", DEFAULT_BATCH_SIZE)
        ),
        help=(
            "Number of meals per OpenRouter request. "
            f"Defaults to MEAL_TRANSLATION_BATCH_SIZE or {DEFAULT_BATCH_SIZE}."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("MEAL_TRANSLATION_WORKERS", DEFAULT_WORKERS)),
        help=(
            "Number of parallel OpenRouter translation requests. "
            f"Defaults to MEAL_TRANSLATION_WORKERS or {DEFAULT_WORKERS}."
        ),
    )
    return parser.parse_args()


def get_target_meals(overwrite_all):
    query = Meal.query
    if not overwrite_all:
        query = query.filter(
            (Meal.description_en.is_(None)) | (Meal.description_en == "")
        )

    return [
        (meal.id, meal.description)
        for meal in query.order_by(Meal.id).with_entities(Meal.id, Meal.description)
    ]


def chunk_meals(meals, batch_size):
    return [meals[index : index + batch_size] for index in range(0, len(meals), batch_size)]


def translate_batch_job(batch):
    descriptions = [description for _, description in batch]
    return batch, translate_meal_batch(descriptions, log=logger)


def commit_translations(batch, translations, overwrite_all):
    success_count = 0
    for meal_id, description in batch:
        english_description = translations.get(description)
        if not english_description:
            continue

        meal = db.session.get(Meal, meal_id)
        if meal is None:
            logger.warning("Skipping meal %s because it no longer exists.", meal_id)
            continue

        if not overwrite_all and meal.description_en:
            continue

        meal.description_en = english_description
        success_count += 1

    if success_count == 0:
        db.session.rollback()
        return 0

    try:
        db.session.commit()
        return success_count
    except Exception as commit_error:
        db.session.rollback()
        logger.error("Failed to commit meal translations: %s", commit_error)
        return 0


def fetch_meal_translations(
    overwrite_all=False,
    batch_size=DEFAULT_BATCH_SIZE,
    workers=DEFAULT_WORKERS,
):
    if not has_configured_translation_api_key():
        logger.error("OPENROUTER_API_KEY is missing or still set to a placeholder.")
        return 2

    if workers < 1:
        logger.error("--workers must be at least 1.")
        return 2
    if batch_size < 1:
        logger.error("--batch-size must be at least 1.")
        return 2

    target_meals = get_target_meals(overwrite_all)
    target_count = len(target_meals)
    if overwrite_all:
        logger.info("Found %s total meals to translate.", target_count)
    else:
        logger.info("Found %s meals missing English translations.", target_count)

    if target_count == 0:
        logger.info("No English meal translations to fetch.")
        return 0

    batches = chunk_meals(target_meals, batch_size)
    worker_count = min(workers, len(batches))
    request_delay_seconds = get_meal_translation_request_delay_seconds()
    processed_count = 0
    failed_count = 0
    next_batch_index = 0
    aborted = False
    start_time = time.time()

    executor = ThreadPoolExecutor(max_workers=worker_count)
    future_to_batch = {}
    in_flight = set()

    def submit_next_job():
        nonlocal next_batch_index
        if next_batch_index >= len(batches):
            return False

        if request_delay_seconds > 0 and next_batch_index > 0:
            time.sleep(request_delay_seconds)

        batch = batches[next_batch_index]
        next_batch_index += 1
        future = executor.submit(translate_batch_job, batch)
        future_to_batch[future] = batch
        in_flight.add(future)
        return True

    try:
        for _ in range(worker_count):
            submit_next_job()

        with tqdm(total=target_count, unit="meal") as progress:
            while in_flight:
                done_futures, in_flight = wait(
                    in_flight, return_when=FIRST_COMPLETED
                )
                for future in done_futures:
                    batch = future_to_batch.pop(future)
                    progress.set_description(f"Batch {batch[0][0]}-{batch[-1][0]}")
                    try:
                        _, translations = future.result()
                    except MPSAuthenticationError:
                        db.session.rollback()
                        logger.error(
                            "Stopping translation fetch because OpenRouter authentication failed."
                        )
                        aborted = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        return 2
                    except Exception as e:
                        failed_count += len(batch)
                        logger.error("Failed to translate batch: %s", e)
                        progress.update(len(batch))
                        submit_next_job()
                        continue

                    committed_count = commit_translations(
                        batch, translations, overwrite_all
                    )
                    processed_count += committed_count
                    failed_count += len(batch) - committed_count
                    progress.update(len(batch))
                    submit_next_job()
    finally:
        executor.shutdown(wait=not aborted, cancel_futures=True)

    logger.info(
        "Meal translation fetch finished in %.2f seconds. Successful: %s. Failed: %s.",
        time.time() - start_time,
        processed_count,
        failed_count,
    )
    return 1 if failed_count else 0


def main():
    configure_logging()
    load_environment()
    args = parse_args()
    app = create_app()
    if app is None:
        return 2

    with app.app_context():
        try:
            db.create_all()
            ensure_application_schema(db)
            return fetch_meal_translations(
                overwrite_all=args.overwrite_all,
                batch_size=args.batch_size,
                workers=args.workers,
            )
        except Exception as e:
            db.session.rollback()
            logger.error("Critical error during meal translation fetch: %s", e)
            logger.error(traceback.format_exc())
            return 1


if __name__ == "__main__":
    sys.exit(main())
