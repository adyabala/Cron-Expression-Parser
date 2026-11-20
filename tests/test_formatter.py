import unittest

from cron_parser.formatter import NAME_WIDTH, format_row, format_table
from cron_parser.parser import parse_expression

EXPECTED_SAMPLE = (
    "minute        0 15 30 45\n"
    "hour          0\n"
    "day of month  1 15\n"
    "month         1 2 3 4 5 6 7 8 9 10 11 12\n"
    "day of week   1 2 3 4 5\n"
    "command       /usr/bin/find"
)


class FormatterTests(unittest.TestCase):
    def test_sample_from_spec(self):
        expr = parse_expression("*/15 0 1,15 * 1-5 /usr/bin/find")
        self.assertEqual(format_table(expr), EXPECTED_SAMPLE)

    def test_name_column_is_fourteen_wide(self):
        self.assertEqual(NAME_WIDTH, 14)
        row = format_row("hour", "0")
        self.assertEqual(row[:14], "hour" + " " * 10)
        self.assertEqual(row[14:], "0")

    def test_every_value_starts_at_column_fifteen(self):
        expr = parse_expression("0 0 * * 0 echo hi")
        for line in format_table(expr).splitlines():
            with self.subTest(line=line):
                self.assertNotEqual(line[14], " ")
                self.assertTrue(line[:14].rstrip())

    def test_rows_are_in_spec_order(self):
        expr = parse_expression("0 0 * * 0 echo hi")
        names = [line[:14].rstrip() for line in format_table(expr).splitlines()]
        self.assertEqual(
            names,
            ["minute", "hour", "day of month", "month", "day of week", "command"],
        )


if __name__ == "__main__":
    unittest.main()
