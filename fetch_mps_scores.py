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

from models import Meal, db
from mps_scoring import (
    MPSAuthenticationError,
    calculate_mps_for_meal,
    get_mps_request_delay_seconds,
    has_configured_mps_api_key,
)
from schema import ensure_application_schema


logger = logging.getLogger("fetch_mps_scores")
DEFAULT_WORKERS = 6


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
        description="Fetch MPS scores for meals using the configured OpenRouter model."
    )
    parser.add_argument(
        "--overwrite-all",
        action="store_true",
        help="Recalculate and overwrite MPS scores for all meals.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("MPS_FETCH_WORKERS", DEFAULT_WORKERS)),
        help=(
            "Number of parallel OpenRouter requests. "
            f"Defaults to MPS_FETCH_WORKERS or {DEFAULT_WORKERS}."
        ),
    )
    return parser.parse_args()


def get_target_meals(overwrite_all):
    query = Meal.query
    if not overwrite_all:
        query = query.filter(Meal.mps_score.is_(None))

    return [
        (meal.id, meal.description)
        for meal in query.order_by(Meal.id).with_entities(Meal.id, Meal.description)
    ]


def calculate_mps_job(meal_id, description):
    return meal_id, description, calculate_mps_for_meal(description, log=logger)


def commit_mps_score(meal_id, description, mps_score, overwrite_all):
    meal = db.session.get(Meal, meal_id)
    if meal is None:
        logger.warning("Skipping meal %s because it no longer exists.", meal_id)
        return False

    if not overwrite_all and meal.mps_score is not None:
        logger.info(
            "Skipping meal %s because it already has MPS %.2f.",
            meal_id,
            meal.mps_score,
        )
        return True

    meal.mps_score = mps_score
    try:
        db.session.commit()
        logger.info(
            "Committed MPS %.2f for meal %s: %s",
            mps_score,
            meal_id,
            description[:80],
        )
        return True
    except Exception as commit_error:
        db.session.rollback()
        logger.error("Failed to commit MPS for meal %s: %s", meal_id, commit_error)
        return False


def fetch_mps_scores(overwrite_all=False, workers=DEFAULT_WORKERS):
    if not has_configured_mps_api_key():
        logger.error("OPENROUTER_API_KEY is missing or still set to a placeholder.")
        return 2

    if workers < 1:
        logger.error("--workers must be at least 1.")
        return 2

    target_meals = get_target_meals(overwrite_all)
    target_count = len(target_meals)
    if overwrite_all:
        logger.info("Found %s total meals to recalculate.", target_count)
    else:
        logger.info("Found %s meals missing MPS scores.", target_count)

    if target_count == 0:
        logger.info("No MPS scores to calculate.")
        return 0

    worker_count = min(workers, target_count)
    logger.info(
        "Starting MPS fetch with %s worker(s). overwrite_all=%s",
        worker_count,
        overwrite_all,
    )
    request_delay_seconds = get_mps_request_delay_seconds()
    processed_count = 0
    failed_count = 0
    start_time = time.time()

    executor = ThreadPoolExecutor(max_workers=worker_count)
    future_to_meal = {}
    in_flight = set()
    next_meal_index = 0
    aborted = False

    def submit_next_job():
        nonlocal next_meal_index
        if next_meal_index >= target_count:
            return False

        if request_delay_seconds > 0 and next_meal_index > 0:
            time.sleep(request_delay_seconds)

        meal_id, description = target_meals[next_meal_index]
        next_meal_index += 1
        future = executor.submit(calculate_mps_job, meal_id, description)
        future_to_meal[future] = (meal_id, description)
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
                    meal_id, description = future_to_meal.pop(future)
                    progress.set_description(f"Meal {meal_id}")
                    try:
                        _, _, mps_score = future.result()
                    except MPSAuthenticationError:
                        db.session.rollback()
                        logger.error(
                            "Stopping MPS fetch because OpenRouter authentication failed. "
                            "Check OPENROUTER_API_KEY."
                        )
                        aborted = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        return 2
                    except Exception as e:
                        failed_count += 1
                        logger.error(
                            "Failed to calculate MPS for meal %s: %s", meal_id, e
                        )
                        progress.update(1)
                        submit_next_job()
                        continue

                    if mps_score is None:
                        failed_count += 1
                        logger.warning(
                            "Failed to calculate MPS for meal %s: %s",
                            meal_id,
                            description[:80],
                        )
                    elif commit_mps_score(
                        meal_id, description, mps_score, overwrite_all
                    ):
                        processed_count += 1
                    else:
                        failed_count += 1

                    progress.update(1)
                    submit_next_job()
    finally:
        executor.shutdown(wait=not aborted, cancel_futures=True)

    logger.info(
        "MPS fetch finished in %.2f seconds. Successful: %s. Failed: %s.",
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

    try:
        with app.app_context():
            db.create_all()
            ensure_application_schema(db)
            return fetch_mps_scores(
                overwrite_all=args.overwrite_all,
                workers=args.workers,
            )
    except Exception as e:
        db.session.rollback()
        logger.error("Critical error during MPS fetch: %s", e)
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
