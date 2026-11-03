#!/usr/bin/env python3
"""ticket-report-cli: turn a CSV of service desk tickets into a weekly report.

Usage:
    python ticket_report.py sample_tickets.csv --week-of 2026-10-26
    python ticket_report.py sample_tickets.csv --week-of 2026-10-26 --out report.txt

Only Python's standard library is used, so there is nothing to install.
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import date, datetime, timedelta

REQUIRED_COLUMNS = ("id", "category", "priority", "status", "created")
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y")

# Different exports name the same status in different ways, so map them to three clean ones.
STATUS_ALIASES = {
    "open": "open",
    "new": "open",
    "in progress": "in progress",
    "in-progress": "in progress",
    "working": "in progress",
    "resolved": "resolved",
    "closed": "resolved",
    "done": "resolved",
}


def parse_date(text):
    """Return a date from a string like 2026-10-27 or 10/27/2026, or None if blank/invalid."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_status(text):
    """Return 'open', 'in progress' or 'resolved', or None for an unknown status."""
    return STATUS_ALIASES.get((text or "").strip().lower())


def week_start(day):
    """Return the Monday of the week that contains `day`."""
    return day - timedelta(days=day.weekday())


def load_tickets(path):
    """Read the CSV. Returns (tickets, skipped) where skipped is a list of (line_number, reason).

    Bad rows are skipped and reported instead of crashing the whole run.
    """
    tickets, skipped = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise ValueError("CSV is missing required column(s): " + ", ".join(missing))
        for line_number, row in enumerate(reader, start=2):  # line 1 is the header
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            created = parse_date(row["created"])
            status = normalize_status(row["status"])
            resolved = parse_date(row.get("resolved", ""))
            if not row["id"]:
                skipped.append((line_number, "missing ticket id"))
            elif created is None:
                skipped.append((line_number, "bad or missing created date"))
            elif status is None:
                skipped.append((line_number, f"unknown status '{row['status']}'"))
            elif status == "resolved" and resolved is None:
                skipped.append((line_number, "resolved ticket has no resolved date"))
            elif resolved is not None and resolved < created:
                skipped.append((line_number, "resolved date is before created date"))
            else:
                tickets.append(
                    {
                        "id": row["id"],
                        "category": row["category"] or "Uncategorized",
                        "priority": (row["priority"] or "unknown").lower(),
                        "status": status,
                        "created": created,
                        "resolved": resolved if status == "resolved" else None,
                    }
                )
    return tickets, skipped


def build_stats(tickets, start):
    """Calculate the numbers for the week that starts on `start` (a Monday)."""
    end = start + timedelta(days=7)  # exclusive
    opened = [t for t in tickets if start <= t["created"] < end]
    resolved = [t for t in tickets if t["resolved"] and start <= t["resolved"] < end]
    # Backlog at the end of the week: created before the week ended and not yet resolved by then.
    backlog = [
        t for t in tickets
        if t["created"] < end and not (t["resolved"] and t["resolved"] < end)
    ]
    days_to_resolve = [(t["resolved"] - t["created"]).days for t in resolved]
    return {
        "start": start,
        "end": end - timedelta(days=1),
        "opened": len(opened),
        "resolved": len(resolved),
        "backlog": len(backlog),
        "net_change": len(opened) - len(resolved),
        "avg_days_to_resolve": (sum(days_to_resolve) / len(days_to_resolve)) if days_to_resolve else None,
        "opened_by_priority": Counter(t["priority"] for t in opened),
        "resolved_by_category": Counter(t["category"] for t in resolved),
    }


def format_report(stats, skipped):
    """Turn the numbers into a plain-text report."""
    lines = [
        f"Weekly Ticket Report: {stats['start']} to {stats['end']}",
        "=" * 52,
        f"Tickets opened:      {stats['opened']}",
        f"Tickets resolved:    {stats['resolved']}",
        f"Backlog at week end: {stats['backlog']}",
    ]
    change = stats["net_change"]
    direction = "grew" if change > 0 else "shrank" if change < 0 else "stayed the same"
    lines.append(f"Backlog {direction} by {abs(change)} this week." if change else "Backlog stayed the same this week.")
    avg = stats["avg_days_to_resolve"]
    lines.append(f"Avg days to resolve: {avg:.1f}" if avg is not None else "Avg days to resolve: n/a (nothing resolved)")

    lines += ["", "Opened by priority:"]
    if stats["opened_by_priority"]:
        for name, count in sorted(stats["opened_by_priority"].items()):
            lines.append(f"  {name:<10} {count}")
    else:
        lines.append("  none")

    lines += ["", "Resolved by category:"]
    if stats["resolved_by_category"]:
        for name, count in stats["resolved_by_category"].most_common():
            lines.append(f"  {name:<18} {count}")
    else:
        lines.append("  none")

    if skipped:
        lines += ["", f"Skipped {len(skipped)} row(s) with problems:"]
        for line_number, reason in skipped:
            lines.append(f"  line {line_number}: {reason}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a weekly report from a CSV of tickets.")
    parser.add_argument("csv_path", help="path to the tickets CSV file")
    parser.add_argument("--week-of", help="any date in the week to report on (YYYY-MM-DD); default is this week")
    parser.add_argument("--out", help="also save the report to this text file")
    args = parser.parse_args(argv)

    day = parse_date(args.week_of) if args.week_of else date.today()
    if day is None:
        parser.error("--week-of must look like 2026-10-26")
    try:
        tickets, skipped = load_tickets(args.csv_path)
    except (OSError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    report = format_report(build_stats(tickets, week_start(day)), skipped)
    print(report, end="")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nSaved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
