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
    """A field spec together with the values it expands to.

    ``values`` is sorted ascending and contains no duplicates.
    """

    spec: FieldSpec
    values: Tuple[int, ...]


@dataclass(frozen=True)
class CronExpression:
    """A fully expanded cron expression.

    ``fields`` are in the same order as the field specs used to parse it.
    ``command`` is the rest of the line, with surrounding whitespace removed.
    """

    fields: Tuple[ExpandedField, ...]
    command: str


def parse_expression(
    text: str, field_specs: Sequence[FieldSpec] = STANDARD_FIELDS
) -> CronExpression:
    """Parse a full cron line: the time fields followed by a command.

    The command is everything after the last time field, kept as written
    (it may contain spaces).

    Args:
        text: The cron line, e.g. ``"*/15 0 1,15 * 1-5 /usr/bin/find"``.
        field_specs: The time fields to expect, in order. Defaults to the
            five standard cron fields.

    Returns:
        A :class:`CronExpression` with every field expanded.

    Raises:
        CronParseError: If the line has too few parts or any field is invalid.
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
    """Expand a single field (e.g. ``"1-10/2,15"``) into a sorted list.

    Raises:
        CronParseError: If the field is empty, malformed or out of range.
            The message starts with the field name.
    """
    if not text:
        raise CronParseError(f"{spec.name}: empty field")
    values = set()
    for item in text.split(","):
        values.update(_parse_item(item, spec, text))
    return sorted(values)


def _parse_item(item: str, spec: FieldSpec, field_text: str) -> List[int]:
    """Expand one comma-separated item: a value, range or step expression.

    An item is split into a base (``*``, ``a`` or ``a-b``) and an optional
    ``/n`` step. New item syntax (for example ``L`` or ``#``) can be added
    here without touching the list handling in :func:`parse_field`.
    """
    if not item:
        raise CronParseError(f"{spec.name}: empty list item in {field_text!r}")

    base, sep, step_text = item.partition("/")
    has_step = bool(sep)
    step = _parse_step(step_text, spec, item) if has_step else 1
    start, end = _parse_bounds(base, spec, item, has_step)
    return [spec.canonical(v) for v in range(start, end + 1, step)]


def _parse_step(text: str, spec: FieldSpec, item: str) -> int:
    """Parse the ``n`` in ``.../n``. It must be a whole number of at least 1."""
    step = _parse_number(text, spec, item, what="step")
    if step == 0:
        raise CronParseError(f"{spec.name}: step must be at least 1 in {item!r}")
    return step


def _parse_bounds(
    base: str, spec: FieldSpec, item: str, has_step: bool
) -> Tuple[int, int]:
    """Return the inclusive ``(start, end)`` that the base of an item covers.

    ``*`` covers the whole field, ``a-b`` covers a to b, and a bare ``a``
    covers just a, or a to the end of the field when followed by a step.
    """
    if base == "*":
        return spec.min_value, spec.max_value

    if "-" in base:
        start_text, _, end_text = base.partition("-")
        start = _parse_value(start_text, spec, item)
        end = _parse_value(end_text, spec, item)
        if start > end:
            raise CronParseError(
                f"{spec.name}: range start is greater than end in {item!r}"
            )
        return start, end

    start = _parse_value(base, spec, item)
    # "a/n" means "from a to the end of the range, every n".
    end = spec.max_value if has_step else start
    if start > end:
        raise CronParseError(
            f"{spec.name}: start {start} is past the end of the range in {item!r}"
        )
    return start, end


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
    """Parse a non-negative decimal integer, without any range check.

    ``what`` ("value" or "step") and ``item`` are only used in the error
    message.
    """
    if not _NUMBER.fullmatch(text):
        raise CronParseError(f"{spec.name}: invalid {what} {text!r} in {item!r}")
    return int(text)
