import unittest
from unittest.mock import Mock, patch

import data_loader


class DataLoaderRefreshTest(unittest.TestCase):
    def test_load_xml_data_to_db_keeps_compatibility_wrapper(self):
        parsed_data = {"Mensa Garbsen": {"01.06.2026": []}}

        with (
            patch("data_loader.parse_mensa_data", return_value=parsed_data) as parse,
            patch(
                "data_loader.load_parsed_mensa_data_to_db",
                return_value=True,
            ) as load_parsed,
        ):
            self.assertTrue(data_loader.load_xml_data_to_db("https://example.test/feed.xml"))

        parse.assert_called_once_with("https://example.test/feed.xml")
        load_parsed.assert_called_once()
        self.assertIs(load_parsed.call_args.args[0], parsed_data)

    def test_load_parsed_mensa_data_to_db_does_not_parse_xml_again(self):
        parsed_data = {"Mensa Garbsen": {"01.06.2026": []}}

        with (
            patch("data_loader.parse_mensa_data", side_effect=AssertionError),
            patch("data_loader.Meal") as meal_model,
            patch("data_loader.MensaMealOccurrence") as occurrence_model,
            patch("data_loader.db") as db_mock,
        ):
            meal_model.query.all.return_value = []
            occurrence_model.query.all.return_value = []
            db_mock.session.commit = Mock()

            self.assertTrue(data_loader.load_parsed_mensa_data_to_db(parsed_data))

        db_mock.session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
