# Cron Expression Parser

A small command-line tool that parses a standard 5-field cron expression and
expands each field to show the exact times it will run.

```
$ python3 -m cron_parser "*/15 0 1,15 * 1-5 /usr/bin/find"
minute        0 15 30 45
hour          0
day of month  1 15
month         1 2 3 4 5 6 7 8 9 10 11 12
day of week   1 2 3 4 5
command       /usr/bin/find
```

Pure Python 3 standard library: no dependencies to install.

---

## Quick start (clean macOS or Linux)

Requirements: Python 3.8 or newer. macOS and most Linux distributions ship
`python3`; check with `python3 --version`. If it is missing:

- macOS: `xcode-select --install` or `brew install python`
- Debian/Ubuntu: `sudo apt-get install -y python3`
- Fedora/RHEL: `sudo dnf install -y python3`

```bash
git clone https://github.com/adyabala/Cron-Expression-Parser.git
cd Cron-Expression-Parser

# Run it
python3 -m cron_parser "*/15 0 1,15 * 1-5 /usr/bin/find"

# Run the tests
python3 -m unittest discover -v
```

That's all. No virtualenv or `pip install` is needed to run or test it.

**Quote the expression.** The program takes the whole cron string as one
argument. Without quotes your shell would split it into several arguments and
expand `*` into file names; the program detects this and asks you to quote it.

You can also pipe the expression in and pass `-` instead, which sidesteps
shell quoting entirely:

```bash
echo "*/15 0 1,15 * 1-5 /usr/bin/find" | python3 -m cron_parser -
```

Other options: `--help` prints usage, `--version` prints the version.

### Optional: install as a `cron-parser` command

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
cron-parser "*/15 0 1,15 * 1-5 /usr/bin/find"
```

### Windows (PowerShell)

```powershell
py -m cron_parser "*/15 0 1,15 * 1-5 /usr/bin/find"
py -m unittest discover -v
```

### Exit codes

| Code | Meaning                                              |
|------|------------------------------------------------------|
| 0    | Success, table printed to stdout                     |
| 1    | Invalid cron expression (message on stderr)          |
| 2    | Wrong usage, e.g. no argument or an unquoted string  |

```
$ python3 -m cron_parser "61 * * * * /bin/true"
error: minute: value 61 out of range 0-59 in '61'
```

---

## Supported syntax

Each of the five time fields accepts numbers only, in any combination of:

| Syntax  | Meaning                                      | Example (minute) | Result             |
|---------|----------------------------------------------|------------------|--------------------|
| `*`     | every value in the field's range             | `*`              | `0 1 2 ... 59`     |
| `a`     | a single value                               | `5`              | `5`                |
| `a-b`   | inclusive range                              | `10-12`          | `10 11 12`         |
| `*/n`   | every n-th value of the whole range          | `*/15`           | `0 15 30 45`       |
| `a-b/n` | every n-th value from a to b                 | `10-30/10`       | `10 20 30`         |
| `a/n`   | every n-th value from a to the end of range  | `5/20`           | `5 25 45`          |
| `x,y,…` | a list of any of the above                   | `0,*/20,7-9`     | `0 7 8 9 20 40`    |

Field ranges:

| Field        | Range | Notes                                  |
|--------------|-------|----------------------------------------|
| minute       | 0-59  |                                        |
| hour         | 0-23  |                                        |
| day of month | 1-31  |                                        |
| month        | 1-12  |                                        |
| day of week  | 0-6   | 0 = Sunday; 7 is also accepted as Sunday and printed as 0 |

Values in each row are sorted ascending with duplicates removed.

Everything after the fifth field is the command, kept exactly as written
(including inner spaces), e.g. `"0 0 * * * /usr/bin/find /tmp -name x"`.

### More examples

Weekday office hours, every 30 minutes from 9:00 to 17:30:

```
$ python3 -m cron_parser "*/30 9-17 * * 1-5 /usr/local/bin/sync"
minute        0 30
hour          9 10 11 12 13 14 15 16 17
day of month  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
month         1 2 3 4 5 6 7 8 9 10 11 12
day of week   1 2 3 4 5
command       /usr/local/bin/sync
```

Quarterly at midnight on the 1st, with a command that has arguments:

```
$ python3 -m cron_parser "0 0 1 1/3 * /usr/bin/backup --full /data"
minute        0
hour          0
day of month  1
month         1 4 7 10
day of week   0 1 2 3 4 5 6
command       /usr/bin/backup --full /data
```

Weekends, with 7 written for Sunday (printed as 0):

```
$ python3 -m cron_parser "15 6 * * 6,7 /bin/weekend-report"
minute        15
hour          6
day of month  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
month         1 2 3 4 5 6 7 8 9 10 11 12
day of week   0 6
command       /bin/weekend-report
```

---

## Approach and design

The code is split so that each piece has one job and new features land in one
obvious place:

```
cron_parser/
  fields.py     # WHAT the fields are: declarative FieldSpec(name, min, max, aliases)
  parser.py     # HOW to expand them: generic, knows nothing about minutes or months
  formatter.py  # HOW to print: the 14-column table
  cli.py        # argument handling, stdout/stderr, exit codes
  errors.py     # CronParseError
  __main__.py   # enables `python -m cron_parser`
tests/
  test_parser.py, test_formatter.py, test_cli.py
```

Flow: `cli.main` → `parser.parse_expression` → `CronExpression` (immutable
dataclasses holding each `FieldSpec` and its expanded values, plus the command)
→ `formatter.format_table` → stdout.

Key decisions:

- **Data-driven fields.** Ranges and aliases live in `FieldSpec` objects. The
  parser takes a sequence of specs, so it can parse a different set of fields
  without modification.
- **Parse into a model, then format.** The parser returns plain data rather than
  strings, so other outputs (JSON, "next run times", etc.) can reuse it.
- **Fail loudly on bad input.** Anything not in the supported syntax raises
  `CronParseError` with the field name and the offending text, rather than
  guessing. The spec says correctness beats completeness.
- **Testable CLI.** `main()` takes `argv`, `stdout` and `stderr` and returns an
  exit code, so it is tested in-process; one end-to-end test also runs
  `python -m cron_parser` as a real subprocess.

---

## Assumptions and limitations

- Exactly five time fields followed by a non-empty command. Fewer is an error.
- Numeric values only. Month and weekday names (`JAN`, `MON`) are **not**
  supported.
- Special strings (`@yearly`, `@reboot`, ...) are not supported, as per the spec.
- Non-standard extensions are not supported: `L`, `W`, `#`, `?`, and
  wrap-around ranges such as `22-2` (a range whose start is above its end is an
  error).
- `a/n` is read as `a-<max>/n`, as in common cron implementations.
- Day of week: 0 and 7 both mean Sunday; output uses 0.
- The tool expands each field independently. It does not check whether a date
  exists (`0 0 31 2 *` is accepted and shows day 31 and month 2), and it does
  not apply cron's rule that day-of-month and day-of-week are OR-ed when both are
  restricted. Both are about *when* a job fires, not about field expansion.
- The command is not validated or executed; it is printed as given.

---

## Troubleshooting

- **`error: expected exactly 1 argument, got 6`**: the expression was not
  quoted, so the shell split it. Wrap it in double quotes, or pipe it in and
  pass `-`.
- **The `*` turned into file names**: same cause. Unquoted `*` is expanded by
  bash and zsh to the files in the current directory. Quote the expression.
- **`zsh: no matches found: */15`**: zsh refuses to run an unquoted glob that
  matches nothing. Quote the expression.
- **`python3: command not found`** (or `python` on Windows opens the Store):
  install Python 3.8+ as described in Quick start. On Windows use `py`.
- **`No module named cron_parser`**: run the command from the repository root
  (the folder that contains `cron_parser/`), or install it with `pip install .`.
- **`error: <field>: ...`**: the expression itself is invalid. The message
  names the field and the text that failed, e.g.
  `error: hour: value 24 out of range 0-23 in '24'`. See
  [Supported syntax](#supported-syntax).

---

## How to extend

Some likely next features and where they go:

- **Add a field** (e.g. a leading seconds field, or a year field): define a new
  `FieldSpec` in `fields.py` and pass a new tuple of specs to
  `parse_expression(text, field_specs=...)`. The parser and formatter need no
  changes.
- **Month / weekday names**: give `FieldSpec` a `names` mapping (e.g.
  `{"JAN": 1, ...}`) and resolve names in `parser._parse_number` before the
  numeric check.
- **Special strings like `@daily`**: map them to their 5-field equivalent in
  `parse_expression` before splitting.
- **New syntax** (`L`, `W`, `#`): extend `parser._parse_item`, which handles one
  comma-separated item.
- **Other output formats** (JSON, next N run times): add a function alongside
  `format_table` that consumes the same `CronExpression` model, and a CLI flag to
  choose it.

Each change should come with tests in the matching `tests/test_*.py` file.

## Running the tests

```bash
python3 -m unittest discover -v              # everything
python3 -m unittest tests.test_parser -v     # one module
```
