"""Command-line entry point.

Usage:
    python -m cron_parser "*/15 0 1,15 * 1-5 /usr/bin/find"
    echo "*/15 0 1,15 * 1-5 /usr/bin/find" | python -m cron_parser -
"""

import sys
from typing import List, Optional, TextIO

from cron_parser import __version__
from cron_parser.errors import CronParseError
from cron_parser.formatter import format_table
from cron_parser.parser import parse_expression

EXIT_OK = 0
EXIT_INVALID_EXPRESSION = 1
EXIT_USAGE = 2

USAGE = """\
usage: python -m cron_parser "<minute> <hour> <day-of-month> <month> <day-of-week> <command>"

Expands a cron expression and prints the times each field will run.
Pass the whole expression as ONE quoted argument, for example:

    python -m cron_parser "*/15 0 1,15 * 1-5 /usr/bin/find"

Use "-" to read the expression from standard input instead, which avoids
shell quoting problems:

    echo "*/15 0 1,15 * 1-5 /usr/bin/find" | python -m cron_parser -

options:
  -h, --help     show this help and exit
  --version      show the version and exit
"""


def main(
    argv: Optional[List[str]] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    stdin: Optional[TextIO] = None,
) -> int:
    """Run the CLI and return a process exit code.

    Args:
        argv: Arguments without the program name. Defaults to ``sys.argv[1:]``.
        stdout: Stream for the table and help text. Defaults to ``sys.stdout``.
        stderr: Stream for error messages. Defaults to ``sys.stderr``.
        stdin: Stream read when the argument is ``-``. Defaults to
            ``sys.stdin``.

    Returns:
        ``EXIT_OK``, ``EXIT_INVALID_EXPRESSION`` or ``EXIT_USAGE``.
    """
    args = sys.argv[1:] if argv is None else argv
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    stdin = stdin or sys.stdin

    if len(args) == 1 and args[0] in ("-h", "--help"):
        stdout.write(USAGE)
        return EXIT_OK

    if len(args) == 1 and args[0] == "--version":
        stdout.write(f"cron-parser {__version__}\n")
        return EXIT_OK

    if len(args) != 1:
        stderr.write(
            f"error: expected exactly 1 argument, got {len(args)}. "
            "Wrap the cron expression in quotes.\n\n"
        )
        stderr.write(USAGE)
        return EXIT_USAGE

    text = stdin.read() if args[0] == "-" else args[0]

    try:
        expression = parse_expression(text)
    except CronParseError as exc:
        stderr.write(f"error: {exc}\n")
        return EXIT_INVALID_EXPRESSION

    stdout.write(format_table(expression) + "\n")
    return EXIT_OK
