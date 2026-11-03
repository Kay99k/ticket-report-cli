# ticket-report-cli

A small Python command-line tool that reads a CSV of service desk tickets and writes a structured weekly report: tickets opened and resolved, backlog, average time to resolve, and breakdowns by priority and category.

I built it to automate the kind of weekly reporting I used to do by hand. **The sample data in this repo is fake.** No real company data is included.

## What it does

- Parses a CSV export of tickets (`id, category, priority, status, created, resolved`).
- **Cleans the data as it reads it:** accepts two date formats (`2026-10-27` and `10/27/2026`), maps different status names (`closed`, `done`, `new`, `working`) to three clean ones, and trims stray whitespace.
- **Skips bad rows instead of crashing,** and lists each skipped row with the reason at the bottom of the report.
- Calculates the numbers for one Monday-to-Sunday week and prints a plain-text report, optionally saving it to a file.

## Run it

Requires Python 3.8 or newer. There is nothing to install.

```bash
python ticket_report.py sample_tickets.csv --week-of 2026-10-26
python ticket_report.py sample_tickets.csv --week-of 2026-10-26 --out report.txt
```

`--week-of` accepts any date in the week you want. If you leave it out, the report covers the current week.

## Example output

```
Weekly Ticket Report: 2026-10-26 to 2026-11-01
====================================================
Tickets opened:      15
Tickets resolved:    13
Backlog at week end: 5
Backlog grew by 2 this week.
Avg days to resolve: 1.8

Opened by priority:
  high       4
  low        4
  medium     7

Resolved by category:
  Hardware           4
  Accounts           3
  Software           3
  Network            2
  Email / Outlook    1

Skipped 2 row(s) with problems:
  line 25: unknown status 'archived'
  line 26: bad or missing created date
```

## Test it

```bash
python -m unittest -v
```

The tests cover date parsing, status cleanup, skipped-row handling, the weekly math, and the report text.

## How it works

| Function | Job |
|---|---|
| `load_tickets` | read the CSV, clean each row, skip and record bad rows |
| `build_stats` | count opened, resolved and backlog for one week; average days to resolve |
| `format_report` | turn the numbers into readable text |
| `main` | handle command-line options |

## Ideas for next steps

- Read from a ticketing system's API instead of a CSV
- Break resolution time down by category
- Export the report as a spreadsheet or email it
