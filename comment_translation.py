import json
import logging
import os
import re
import time

import requests

from i18n import normalize_language
from mps_scoring import (
    MPSAuthenticationError,
    get_ai_max_tokens,
    get_ai_model,
    get_openrouter_base_url,
    is_mps_api_key_configured,
)


logger = logging.getLogger(__name__)

DEFAULT_PROMPT_COMMENT_TRANSLATION = """Translate this mensa meal comment between German and English.
Return strict JSON only with both keys "de" and "en".
Keep the tone, slang, names, and food references. Do not add explanation.

Original language: {source_language}
Comment:
{comment_text}"""


def parse_comment_translation_response(response_text):
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
        raise ValueError("comment translation response must be a JSON object")

    return {
        "de": parsed.get("de", "").strip()
        if isinstance(parsed.get("de"), str)
        else "",
        "en": parsed.get("en", "").strip()
        if isinstance(parsed.get("en"), str)
        else "",
    }


def translate_comment_text(comment_text, source_language, log=None):
    log = log or logger
    comment_text = (comment_text or "").strip()
    source_language = normalize_language(source_language)
    if not comment_text:
        return {"de": "", "en": "", "translation_failed": False}

    fallback = {
        "de": comment_text if source_language == "de" else "",
        "en": comment_text if source_language == "en" else "",
        "translation_failed": True,
    }

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not is_mps_api_key_configured(api_key):
        log.warning("OPENROUTER_API_KEY not found for comment translation")
        return fallback

    prompt_template = os.environ.get(
        "PROMPT_COMMENT_TRANSLATION", DEFAULT_PROMPT_COMMENT_TRANSLATION
    ).replace("\\n", "\n")
    prompt = (
        prompt_template.replace("{source_language}", source_language)
        .replace("{comment_text}", comment_text)
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    max_retries = 2
    base_delay = 1
    for attempt in range(max_retries):
        try:
            request_start = time.time()
            log.info(
                "Requesting comment translation from OpenRouter (attempt %s/%s)",
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
                timeout=30,
            )
            log.info(
                "OpenRouter comment translation response status=%s duration=%.2fs",
                response.status_code,
                time.time() - request_start,
            )

            if response.status_code == 200:
                result = response.json()
                response_text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                translated = parse_comment_translation_response(response_text)
                translated[source_language] = translated[source_language] or comment_text
                translated["translation_failed"] = not (
                    translated.get("de") and translated.get("en")
                )
                return translated

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2**attempt))
                    continue
                return fallback

            if response.status_code in (401, 403):
                raise MPSAuthenticationError("OpenRouter rejected OPENROUTER_API_KEY")

            log.error(
                "OpenRouter comment translation API error: %s - %s",
                response.status_code,
                response.text,
            )
            return fallback
        except MPSAuthenticationError:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning("Comment translation retry after error: %s", e)
                time.sleep(base_delay * (2**attempt))
                continue
            log.error("Error translating comment: %s", e)
            return fallback

    return fallback


def choose_comment_text(comment, language):
    language = normalize_language(language)
    preferred = comment.text_en if language == "en" else comment.text_de
    fallback = comment.text_de if language == "en" else comment.text_en
    return preferred or fallback or ""
