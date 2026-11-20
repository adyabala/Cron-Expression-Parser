"""Parse cron expressions into explicit, expanded values.

Supported syntax per field (numbers only):

    *         every value in the field's range
    a         a single value
    a-b       an inclusive range
    */n       every n-th value across the whole range
    a-b/n     every n-th value from a up to b
    a/n       every n-th value from a up to the end of the range
    x,y,...   a list of any of the above

Results are sorted and deduplicated.
"""

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from cron_parser.errors import CronParseError
from cron_parser.fields import STANDARD_FIELDS, FieldSpec

_NUMBER = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class ExpandedField:
    """A field spec together with the values it expands to."""

    spec: FieldSpec
    values: Tuple[int, ...]


@dataclass(frozen=True)
class CronExpression:
    """A fully expanded cron expression."""

    fields: Tuple[ExpandedField, ...]
    command: str


def parse_expression(
    text: str, field_specs: Sequence[FieldSpec] = STANDARD_FIELDS
) -> CronExpression:
    """Parse a full cron line: the time fields followed by a command.

    The command is everything after the last time field, kept as written
    (it may contain spaces).
    """
    if text is None:
        raise CronParseError("cron expression is empty")
    n_fields = len(field_specs)
    parts = text.strip().split(None, n_fields)
    if len(parts) < n_fields + 1:
        raise CronParseError(
            f"expected {n_fields} time fields followed by a command, "
            f"got {len(parts)} item(s): {text.strip()!r}"
        )
    *field_texts, command = parts
    expanded = tuple(
        ExpandedField(spec, tuple(parse_field(field_text, spec)))
        for field_text, spec in zip(field_texts, field_specs)
    )
    return CronExpression(fields=expanded, command=command)


def parse_field(text: str, spec: FieldSpec) -> List[int]:
    """Expand a single field (e.g. ``"1-10/2,15"``) into a sorted list."""
    if not text:
        raise CronParseError(f"{spec.name}: empty field")
    values = set()
    for item in text.split(","):
        values.update(_parse_item(item, spec, text))
    return sorted(values)


def _parse_item(item: str, spec: FieldSpec, field_text: str) -> List[int]:
    """Expand one comma-separated item: a value, range or step expression."""
    if not item:
        raise CronParseError(f"{spec.name}: empty list item in {field_text!r}")

    base, sep, step_text = item.partition("/")
    if sep:
        step = _parse_number(step_text, spec, item, what="step")
        if step == 0:
            raise CronParseError(f"{spec.name}: step must be at least 1 in {item!r}")
    else:
        step = 1

    if base == "*":
        start, end = spec.min_value, spec.max_value
    elif "-" in base:
        start_text, _, end_text = base.partition("-")
        start = _parse_value(start_text, spec, item)
        end = _parse_value(end_text, spec, item)
        if start > end:
            raise CronParseError(
                f"{spec.name}: range start is greater than end in {item!r}"
            )
    else:
        start = _parse_value(base, spec, item)
        # "a/n" means "from a to the end of the range, every n".
        end = spec.max_value if sep else start
        if start > end:
            raise CronParseError(
                f"{spec.name}: start {start} is past the end of the range in {item!r}"
            )

    return [spec.canonical(v) for v in range(start, end + 1, step)]


def _parse_value(text: str, spec: FieldSpec, item: str) -> int:
    """Parse a number and check it is allowed for this field."""
    value = _parse_number(text, spec, item, what="value")
    if not spec.min_accepted <= value <= spec.max_accepted:
        raise CronParseError(
            f"{spec.name}: value {value} out of range "
            f"{spec.min_accepted}-{spec.max_accepted} in {item!r}"
        )
    return value


def _parse_number(text: str, spec: FieldSpec, item: str, what: str) -> int:
    if not _NUMBER.fullmatch(text):
        raise CronParseError(f"{spec.name}: invalid {what} {text!r} in {item!r}")
    return int(text)
