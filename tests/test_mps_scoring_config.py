import os
import unittest
from unittest.mock import patch

from mps_scoring import get_ai_max_tokens_max, get_ai_model_max


class MpsScoringConfigTest(unittest.TestCase):
    def test_ai_model_max_uses_specific_model_when_set(self):
        with patch.dict(
            os.environ,
            {"AI_MODEL": "base/model", "AI_MODEL_MAX": "recommendation/model"},
            clear=True,
        ):
            self.assertEqual(get_ai_model_max(), "recommendation/model")

    def test_ai_model_max_falls_back_to_ai_model(self):
        with patch.dict(os.environ, {"AI_MODEL": "base/model"}, clear=True):
            self.assertEqual(get_ai_model_max(), "base/model")

    def test_ai_max_tokens_max_uses_specific_limit_when_set(self):
        with patch.dict(
            os.environ,
            {"AI_MAX_TOKENS": "500", "AI_MAX_TOKENS_MAX": "1200"},
            clear=True,
        ):
            self.assertEqual(get_ai_max_tokens_max(), 1200)

    def test_ai_max_tokens_max_falls_back_to_ai_max_tokens(self):
        with patch.dict(os.environ, {"AI_MAX_TOKENS": "500"}, clear=True):
            self.assertEqual(get_ai_max_tokens_max(), 500)


if __name__ == "__main__":
    unittest.main()
