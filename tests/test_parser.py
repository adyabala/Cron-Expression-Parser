import unittest

from cron_parser.errors import CronParseError
from cron_parser.fields import (
    DAY_OF_MONTH,
    DAY_OF_WEEK,
    HOUR,
    MINUTE,
    MONTH,
    FieldSpec,
)
from cron_parser.parser import parse_expression, parse_field


class ParseFieldTests(unittest.TestCase):
    def test_wildcard_expands_to_full_range(self):
        self.assertEqual(parse_field("*", MINUTE), list(range(0, 60)))
        self.assertEqual(parse_field("*", HOUR), list(range(0, 24)))
        self.assertEqual(parse_field("*", DAY_OF_MONTH), list(range(1, 32)))
        self.assertEqual(parse_field("*", MONTH), list(range(1, 13)))
        self.assertEqual(parse_field("*", DAY_OF_WEEK), list(range(0, 7)))

    def test_single_value(self):
        self.assertEqual(parse_field("5", MINUTE), [5])

    def test_range(self):
        self.assertEqual(parse_field("1-5", DAY_OF_WEEK), [1, 2, 3, 4, 5])

    def test_single_value_range(self):
        self.assertEqual(parse_field("3-3", HOUR), [3])

    def test_step_over_wildcard(self):
        self.assertEqual(parse_field("*/15", MINUTE), [0, 15, 30, 45])

    def test_step_over_wildcard_respects_field_minimum(self):
        self.assertEqual(parse_field("*/5", DAY_OF_MONTH), [1, 6, 11, 16, 21, 26, 31])

    def test_step_over_range(self):
        self.assertEqual(parse_field("10-20/5", MINUTE), [10, 15, 20])

    def test_step_larger_than_range(self):
        self.assertEqual(parse_field("*/100", MINUTE), [0])

    def test_start_with_step_runs_to_end_of_range(self):
        self.assertEqual(parse_field("5/20", MINUTE), [5, 25, 45])

    def test_list(self):
        self.assertEqual(parse_field("1,15", DAY_OF_MONTH), [1, 15])

    def test_list_is_sorted_and_deduplicated(self):
        self.assertEqual(parse_field("30,5,1-6,5", MINUTE), [1, 2, 3, 4, 5, 6, 30])

    def test_list_of_mixed_items(self):
        self.assertEqual(
            parse_field("0,*/20,7-9,50-59/4", MINUTE),
            [0, 7, 8, 9, 20, 40, 50, 54, 58],
        )

    def test_boundaries_are_accepted(self):
        self.assertEqual(parse_field("0,59", MINUTE), [0, 59])
        self.assertEqual(parse_field("1,12", MONTH), [1, 12])

    def test_seven_means_sunday_in_day_of_week(self):
        self.assertEqual(parse_field("7", DAY_OF_WEEK), [0])
        self.assertEqual(parse_field("5-7", DAY_OF_WEEK), [0, 5, 6])
        self.assertEqual(parse_field("0,7", DAY_OF_WEEK), [0])

    def test_invalid_fields_raise(self):
        cases = [
            ("", MINUTE),          # empty
            ("60", MINUTE),        # above range
            ("24", HOUR),
            ("0", DAY_OF_MONTH),   # below range
            ("32", DAY_OF_MONTH),
            ("0", MONTH),
            ("13", MONTH),
            ("8", DAY_OF_WEEK),
        ]
        for text, spec in cases:
            with self.subTest(text=text, field=spec.name):
                with self.assertRaises(CronParseError):
                    parse_field(text, spec)

    def test_malformed_syntax_raises(self):
        for text in [
            "abc", "1,", ",1", "1,,2", "5-", "-5", "1-2-3", "10-5",
            "*/0", "*/", "/5", "*/x", "**", "1.5", "+1", " 1", "MON", "²",
            "1/2/3", "*-5",
        ]:
            with self.subTest(text=text):
                with self.assertRaises(CronParseError):
                    parse_field(text, MINUTE)

    def test_value_above_max_is_rejected_without_alias(self):
        no_alias = FieldSpec("weekday", 0, 6)
        with self.assertRaises(CronParseError):
            parse_field("7", no_alias)

    def test_custom_field_spec(self):
        seconds = FieldSpec("second", 0, 59)
        self.assertEqual(parse_field("*/20", seconds), [0, 20, 40])

    def test_error_message_names_the_field(self):
        with self.assertRaisesRegex(CronParseError, "^hour: value 25 out of range"):
            parse_field("25", HOUR)


class ParseExpressionTests(unittest.TestCase):
    def test_sample_from_spec(self):
        expr = parse_expression("*/15 0 1,15 * 1-5 /usr/bin/find")
        self.assertEqual(
            [(f.spec.name, f.values) for f in expr.fields],
            [
                ("minute", (0, 15, 30, 45)),
                ("hour", (0,)),
                ("day of month", (1, 15)),
                ("month", tuple(range(1, 13))),
                ("day of week", (1, 2, 3, 4, 5)),
            ],
        )
        self.assertEqual(expr.command, "/usr/bin/find")

    def test_command_with_arguments_is_kept_intact(self):
        expr = parse_expression("0 0 * * * /usr/bin/find /tmp -name '*.log'  -delete")
        self.assertEqual(expr.command, "/usr/bin/find /tmp -name '*.log'  -delete")

    def test_extra_whitespace_between_fields_is_ignored(self):
        expr = parse_expression("  */15\t0  1,15 *   1-5   /usr/bin/find  ")
        self.assertEqual(expr.fields[0].values, (0, 15, 30, 45))
        self.assertEqual(expr.command, "/usr/bin/find")

    def test_missing_command_raises(self):
        with self.assertRaisesRegex(CronParseError, "expected 5 time fields"):
            parse_expression("*/15 0 1,15 * 1-5")

    def test_too_few_fields_raises(self):
        with self.assertRaises(CronParseError):
            parse_expression("*/15 0 /usr/bin/find")

    def test_empty_input_raises(self):
        for text in ["", "   ", None]:
            with self.subTest(text=text):
                with self.assertRaises(CronParseError):
                    parse_expression(text)

    def test_invalid_field_in_expression_raises(self):
        with self.assertRaisesRegex(CronParseError, "^day of month"):
            parse_expression("0 0 32 * * cmd")


if __name__ == "__main__":
    unittest.main()
