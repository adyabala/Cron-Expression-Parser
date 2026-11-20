"""Allow running the package with ``python -m cron_parser``."""

import sys

from cron_parser.cli import main

if __name__ == "__main__":
    sys.exit(main())
