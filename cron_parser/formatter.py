"""Render a parsed cron expression as the output table."""

from typing import List

from cron_parser.parser import CronExpression

#: Width of the field-name column, as required by the spec.
NAME_WIDTH = 14


def format_row(name: str, value: str, width: int = NAME_WIDTH) -> str:
    """One table row: the name padded to ``width`` columns, then the value."""
    return f"{name:<{width}}{value}"


def format_table(expression: CronExpression, width: int = NAME_WIDTH) -> str:
    """Render every field plus the command, one row per line."""
    rows: List[str] = [
        format_row(f.spec.name, " ".join(str(v) for v in f.values), width)
        for f in expression.fields
    ]
    rows.append(format_row("command", expression.command, width))
    return "\n".join(rows)
