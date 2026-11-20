"""Declarative description of the cron time fields.

Each field is described by a :class:`FieldSpec`. The parser is generic and knows
nothing about minutes or months; everything field-specific lives here. Adding a
new field (for example a leading "seconds" field) or changing a range means
adding or editing a spec, not touching the parser.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class FieldSpec:
    """Describes one cron time field.

    Attributes:
        name: Label printed in the output table.
        min_value: Smallest value the field can expand to.
        max_value: Largest value the field can expand to.
        aliases: Extra numeric values accepted in the input and the canonical
            value they map to, e.g. ``{7: 0}`` so that 7 means Sunday in the
            day-of-week field. Aliases may lie outside ``min_value..max_value``.
    """

    name: str
    min_value: int
    max_value: int
    aliases: Dict[int, int] = field(default_factory=dict)

    @property
    def max_accepted(self) -> int:
        """Largest number accepted in the input, including aliases."""
        return max([self.max_value, *self.aliases])

    @property
    def min_accepted(self) -> int:
        """Smallest number accepted in the input, including aliases."""
        return min([self.min_value, *self.aliases])

    def canonical(self, value: int) -> int:
        """Map an accepted input value to the value that is printed."""
        return self.aliases.get(value, value)


MINUTE = FieldSpec("minute", 0, 59)
HOUR = FieldSpec("hour", 0, 23)
DAY_OF_MONTH = FieldSpec("day of month", 1, 31)
MONTH = FieldSpec("month", 1, 12)
# 0 and 7 both mean Sunday, as in most cron implementations. 7 is printed as 0.
DAY_OF_WEEK = FieldSpec("day of week", 0, 6, aliases={7: 0})

#: The five standard fields, in the order they appear in a cron expression.
STANDARD_FIELDS: Tuple[FieldSpec, ...] = (
    MINUTE,
    HOUR,
    DAY_OF_MONTH,
    MONTH,
    DAY_OF_WEEK,
)
