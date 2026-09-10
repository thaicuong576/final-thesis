import unittest
from datetime import date

from thesis_data.periods import validate_period_bounds


class PeriodBoundsTests(unittest.TestCase):
    def test_quarter_two_ends_on_june_thirtieth(self):
        self.assertEqual(
            validate_period_bounds("2024_Q2"),
            (date(2024, 4, 1), date(2024, 6, 30)),
        )


    def test_quarter_three_ends_on_september_thirtieth(self):
        self.assertEqual(
            validate_period_bounds("2024_Q3"),
            (date(2024, 7, 1), date(2024, 9, 30)),
        )


    def test_unknown_quarter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "YYYY_QN"):
            validate_period_bounds("2024_Q5")
