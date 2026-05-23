import json
import logging
import os
import re
import time

import requests

from mps_scoring import (
    MPSAuthenticationError,
    get_ai_max_tokens,
    get_ai_model,
    get_openrouter_base_url,
    is_mps_api_key_configured,
)


logger = logging.getLogger(__name__)

MEAL_TRANSLATION_REQUEST_DELAY_SECONDS_DEFAULT = "0.5"

DEFAULT_PROMPT_MEAL_TRANSLATION = """Translate the following German mensa meal names into natural, concise English.
Preserve dish style, ingredient meaning, allergens, and preparation details. Keep brand names, mensa-specific names, and proper nouns unchanged.
Return strict JSON only: an object whose keys are the exact German inputs and whose values are English translations.

German meal names:
{meal_list}"""


def get_meal_translation_request_delay_seconds():
    return float(
        os.environ.get(
            "MEAL_TRANSLATION_REQUEST_DELAY_SECONDS",
            MEAL_TRANSLATION_REQUEST_DELAY_SECONDS_DEFAULT,
        )
    )


def has_configured_translation_api_key():
    return is_mps_api_key_configured(os.environ.get("OPENROUTER_API_KEY", ""))


def get_translation_prompt(descriptions):
    meal_list = "\n".join(f"- {description}" for description in descriptions)
    prompt_template = os.environ.get(
        "PROMPT_MEAL_TRANSLATION", DEFAULT_PROMPT_MEAL_TRANSLATION
    )
    return prompt_template.replace("{meal_list}", meal_list)


def parse_translation_response(response_text, expected_descriptions):
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[len("```") :].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("translation response must be a JSON object")

    expected_set = set(expected_descriptions)
    translations = {}
    for german, english in parsed.items():
        if german not in expected_set or not isinstance(english, str):
            continue
        english = english.strip()
        if english:
            translations[german] = english
    return translations


def translate_meal_batch(descriptions, log=None):
    log = log or logger
    descriptions = [description for description in descriptions if description]
    if not descriptions:
        return {}

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not is_mps_api_key_configured(api_key):
        log.error("OPENROUTER_API_KEY not found for meal translation")
        return {}

    max_retries = 3
    base_delay = 2
    prompt = get_translation_prompt(descriptions)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for attempt in range(max_retries):
        try:
            request_start = time.time()
            log.info(
                "Requesting English translations for %s meal(s) (attempt %s/%s)",
                len(descriptions),
                attempt + 1,
                max_retries,
            )
            response = requests.post(
                get_openrouter_base_url(),
                headers=headers,
                json={
                    "model": get_ai_model(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": get_ai_max_tokens(),
                },
                timeout=45,
            )
            log.info(
                "OpenRouter translation response status=%s duration=%.2fs batch_size=%s",
                response.status_code,
                time.time() - request_start,
                len(descriptions),
            )

            if response.status_code == 200:
                result = response.json()
                response_text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return parse_translation_response(response_text, descriptions)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    log.warning(
                        "OpenRouter translation retry in %s seconds after status %s",
                        delay,
                        response.status_code,
                    )
                    time.sleep(delay)
                    continue
                log.error(
                    "OpenRouter translation failed after %s attempts: %s - %s",
                    max_retries,
                    response.status_code,
                    response.text,
                )
                return {}

            if response.status_code in (401, 403):
                log.error(
                    "OpenRouter authentication failed for meal translation: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise MPSAuthenticationError("OpenRouter rejected OPENROUTER_API_KEY")

            log.error(
                "OpenRouter translation API error: %s - %s",
                response.status_code,
                response.text,
            )
            return {}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                log.warning(
                    "Translation request timeout, retrying in %s seconds", delay
                )
                time.sleep(delay)
                continue
            log.error("Translation request timeout after %s attempts", max_retries)
            return {}
        except MPSAuthenticationError:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                log.warning(
                    "Translation error, retrying in %s seconds: %s", delay, e
                )
                time.sleep(delay)
                continue
            log.error("Error translating meal batch: %s", e)
            return {}

    return {}
