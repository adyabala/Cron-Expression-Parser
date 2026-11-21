import io
import os
import subprocess
import sys
import unittest

from cron_parser import __version__, cli
from tests.test_formatter import EXPECTED_SAMPLE

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_main(*args, stdin_text=""):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(
        list(args), stdout=out, stderr=err, stdin=io.StringIO(stdin_text)
    )
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_sample_from_spec(self):
        code, out, err = run_main("*/15 0 1,15 * 1-5 /usr/bin/find")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(out, EXPECTED_SAMPLE + "\n")
        self.assertEqual(err, "")

    def test_invalid_expression_reports_on_stderr(self):
        code, out, err = run_main("61 * * * * cmd")
        self.assertEqual(code, cli.EXIT_INVALID_EXPRESSION)
        self.assertEqual(out, "")
        self.assertIn("minute: value 61 out of range", err)

    def test_no_arguments_is_usage_error(self):
        code, out, err = run_main()
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertEqual(out, "")
        self.assertIn("usage:", err)

    def test_unquoted_expression_is_usage_error(self):
        code, _, err = run_main("*/15", "0", "1,15", "*", "1-5", "/usr/bin/find")
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("quotes", err)

    def test_help(self):
        code, out, err = run_main("--help")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("usage:", out)
        self.assertEqual(err, "")

    def test_version(self):
        code, out, err = run_main("--version")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(out, f"cron-parser {__version__}\n")
        self.assertEqual(err, "")

    def test_dash_reads_expression_from_stdin(self):
        code, out, err = run_main(
            "-", stdin_text="*/15 0 1,15 * 1-5 /usr/bin/find\n"
        )
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(out, EXPECTED_SAMPLE + "\n")
        self.assertEqual(err, "")

    def test_empty_stdin_is_invalid_expression(self):
        code, out, err = run_main("-", stdin_text="")
        self.assertEqual(code, cli.EXIT_INVALID_EXPRESSION)
        self.assertEqual(out, "")
        self.assertIn("error:", err)

    def test_invalid_expression_from_stdin(self):
        code, _, err = run_main("-", stdin_text="* * * * 9 cmd")
        self.assertEqual(code, cli.EXIT_INVALID_EXPRESSION)
        self.assertIn("day of week", err)


class ModuleEntryPointTests(unittest.TestCase):
    """End-to-end: run ``python -m cron_parser`` as a real process."""

    def run_module(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "cron_parser", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            input=input_text,
        )

    def test_sample_from_spec(self):
        result = self.run_module("*/15 0 1,15 * 1-5 /usr/bin/find")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace("\r\n", "\n"), EXPECTED_SAMPLE + "\n")

    def test_invalid_expression_exits_nonzero(self):
        result = self.run_module("* * * * *")
        self.assertEqual(result.returncode, cli.EXIT_INVALID_EXPRESSION)
        self.assertIn("error:", result.stderr)

    def test_expression_piped_on_stdin(self):
        result = self.run_module("-", input_text="*/15 0 1,15 * 1-5 /usr/bin/find\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace("\r\n", "\n"), EXPECTED_SAMPLE + "\n")


if __name__ == "__main__":
    unittest.main()
