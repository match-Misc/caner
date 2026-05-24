import logging
import os
import time

import requests


OPENROUTER_BASE_URL_DEFAULT = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL_DEFAULT = "mistralai/mistral-small"
AI_MAX_TOKENS_DEFAULT = "500"
MPS_REQUEST_DELAY_SECONDS_DEFAULT = "0.5"
MPS_KEY_PLACEHOLDERS = {"", "your_openrouter_api_key_here", "changeme", "change_me"}


DEFAULT_PROMPT_MPS = """Du bist Max, ein Fitness-Enthusiast, der sich strikt an eine bestimmte Ernährung hält. Max meidet konsequent alles, was mit Gemüse oder Obst zu tun hat - das betrifft nicht nur offensichtliche Zutaten wie Zucchini, Paprika oder Äpfel, sondern auch Dinge wie Salat, Zwiebeln, Pilze oder Beeren. Auch Fisch lehnt er komplett ab, unabhängig von der Zubereitungsart. Er bevorzugt klare, einfache Gerichte ohne "grünes Zeug" oder pflanzliche Komponenten, die im Geschmack dominant sind.

Dafür isst Max gerne herzhafte, proteinreiche Speisen wie Fleischgerichte (z. B. Schwein, Rind, Huhn), Käse oder Eier. Aufgrund seines regelmäßigen Trainings im Fitnessstudio legt er zudem Wert auf einen hohen Proteingehalt, weshalb eiweißreiche Mahlzeiten bei ihm besonders gut ankommen. Neutrale Beilagen wie Reis, Kartoffeln oder Pasta sind für ihn in Ordnung, solange sie nicht mit Gemüse kombiniert sind. Süßspeisen ohne Obst sind ebenfalls gern gesehen.

Bewerte das folgende Gericht auf einer Skala von 0 bis 100, wobei 100 die perfekte Übereinstimmung mit Max' Vorlieben darstellt:

Gericht: {meal_description}

Gib nur eine Zahl zwischen 0 und 100 zurück, die die Bewertung darstellt. Kein zusätzlicher Text."""

logger = logging.getLogger(__name__)


class MPSAuthenticationError(Exception):
    """Raised when OpenRouter rejects the configured API key."""


def get_openrouter_base_url():
    return os.environ.get("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL_DEFAULT)


def get_ai_model():
    return os.environ.get("AI_MODEL", AI_MODEL_DEFAULT)


def get_ai_model_max():
    return os.environ.get("AI_MODEL_MAX", get_ai_model())


def get_ai_max_tokens():
    return int(os.environ.get("AI_MAX_TOKENS", AI_MAX_TOKENS_DEFAULT))


def get_ai_max_tokens_max():
    return int(os.environ.get("AI_MAX_TOKENS_MAX", get_ai_max_tokens()))


def get_mps_request_delay_seconds():
    return float(
        os.environ.get(
            "MPS_REQUEST_DELAY_SECONDS", MPS_REQUEST_DELAY_SECONDS_DEFAULT
        )
    )


def is_mps_api_key_configured(api_key):
    return bool(api_key) and api_key.strip().lower() not in MPS_KEY_PLACEHOLDERS


def has_configured_mps_api_key():
    return is_mps_api_key_configured(os.environ.get("OPENROUTER_API_KEY", ""))


def calculate_mps_for_meal(meal_description, log=None):
    """Calculate MPS score for a single meal using the API with retry logic."""
    log = log or logger
    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        try:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not is_mps_api_key_configured(api_key):
                log.error("OPENROUTER_API_KEY not found for MPS calculation")
                return None

            prompt_template = os.environ.get("PROMPT_MPS", DEFAULT_PROMPT_MPS)
            prompt = prompt_template.replace("{meal_description}", meal_description)

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            request_start = time.time()
            log.info(
                "Requesting MPS score from OpenRouter for meal '%s' (attempt %s/%s)",
                meal_description[:80],
                attempt + 1,
                max_retries,
            )
            response = requests.post(
                get_openrouter_base_url(),
                headers=headers,
                json={
                    "model": get_ai_model(),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": get_ai_max_tokens(),
                },
                timeout=30,
            )
            request_duration = time.time() - request_start
            log.info(
                "OpenRouter MPS response status=%s duration=%.2fs meal='%s'",
                response.status_code,
                request_duration,
                meal_description[:80],
            )

            if response.status_code == 200:
                result = response.json()
                mps_text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                try:
                    mps_score = float(mps_text)
                    bounded_score = max(0, min(100, mps_score))
                    log.info(
                        "Parsed MPS score %.2f for meal '%s'",
                        bounded_score,
                        meal_description[:80],
                    )
                    return bounded_score
                except ValueError:
                    log.warning("Could not parse MPS score: %s", mps_text)
                    return None

            if response.status_code == 429:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    log.warning(
                        "Rate limit exceeded, retrying in %s seconds (attempt %s/%s)",
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue

                log.error("Rate limit exceeded after %s attempts", max_retries)
                return None

            if response.status_code >= 500:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    log.warning(
                        "Server error %s, retrying in %s seconds (attempt %s/%s)",
                        response.status_code,
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue

                log.error(
                    "Server error %s after %s attempts",
                    response.status_code,
                    max_retries,
                )
                return None

            if response.status_code in (401, 403):
                log.error(
                    "OpenRouter authentication failed for MPS calculation: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise MPSAuthenticationError("OpenRouter rejected OPENROUTER_API_KEY")

            log.error(
                "OpenRouter API error: %s - %s", response.status_code, response.text
            )
            return None

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                log.warning(
                    "Request timeout, retrying in %s seconds (attempt %s/%s)",
                    delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(delay)
                continue

            log.error("Request timeout after %s attempts", max_retries)
            return None

        except MPSAuthenticationError:
            raise

        except Exception as e:
            log.error("Error calculating MPS: %s", str(e))
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                log.warning(
                    "Exception occurred, retrying in %s seconds (attempt %s/%s)",
                    delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(delay)
                continue

            return None

    return None
