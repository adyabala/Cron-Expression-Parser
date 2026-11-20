"""Exceptions raised by the cron parser."""


class CronParseError(ValueError):
    """Raised when a cron expression (or one of its fields) is invalid."""
