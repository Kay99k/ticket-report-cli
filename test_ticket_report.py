import os
import tempfile
import unittest
from datetime import date

import ticket_report as tr


def write_csv(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


class ParsingTests(unittest.TestCase):
    def test_parse_date_accepts_both_formats(self):
        self.assertEqual(tr.parse_date("2026-10-27"), date(2026, 10, 27))
        self.assertEqual(tr.parse_date("10/27/2026"), date(2026, 10, 27))

    def test_parse_date_rejects_bad_input(self):
        self.assertIsNone(tr.parse_date("not-a-date"))
        self.assertIsNone(tr.parse_date(""))
        self.assertIsNone(tr.parse_date(None))

    def test_normalize_status(self):
        self.assertEqual(tr.normalize_status("Closed"), "resolved")
        self.assertEqual(tr.normalize_status(" In-Progress "), "in progress")
        self.assertEqual(tr.normalize_status("NEW"), "open")
        self.assertIsNone(tr.normalize_status("archived"))

    def test_week_start_is_monday(self):
        self.assertEqual(tr.week_start(date(2026, 10, 30)), date(2026, 10, 26))  # a Friday
        self.assertEqual(tr.week_start(date(2026, 10, 26)), date(2026, 10, 26))  # already Monday


class LoadTests(unittest.TestCase):
    def test_bad_rows_are_skipped_not_fatal(self):
        path = write_csv(
            "id,category,priority,status,created,resolved\n"
            "A1,Hardware,high,resolved,2026-10-26,2026-10-27\n"
            "A2,Hardware,low,archived,2026-10-26,\n"
            "A3,Hardware,low,resolved,bad-date,2026-10-27\n"
            "A4,Hardware,low,resolved,2026-10-26,\n"
            "A5,Hardware,low,resolved,2026-10-28,2026-10-27\n"
        )
        self.addCleanup(os.remove, path)
        tickets, skipped = tr.load_tickets(path)
        self.assertEqual([t["id"] for t in tickets], ["A1"])
        self.assertEqual(len(skipped), 4)

    def test_missing_column_raises(self):
        path = write_csv("id,category\nA1,Hardware\n")
        self.addCleanup(os.remove, path)
        with self.assertRaises(ValueError):
            tr.load_tickets(path)


class StatsTests(unittest.TestCase):
    def setUp(self):
        def t(id, created, resolved=None, cat="Hardware", pri="low"):
            return {"id": id, "category": cat, "priority": pri,
                    "status": "resolved" if resolved else "open",
                    "created": created, "resolved": resolved}
        self.tickets = [
            t("1", date(2026, 10, 26), date(2026, 10, 28)),   # opened and resolved this week, 2 days
            t("2", date(2026, 10, 27), None, pri="high"),     # opened, still open
            t("3", date(2026, 10, 20), date(2026, 10, 27)),   # opened last week, resolved this week
            t("4", date(2026, 10, 21), None),                 # old, still open
            t("5", date(2026, 11, 3), None),                  # next week: must not count
        ]

    def test_counts(self):
        s = tr.build_stats(self.tickets, date(2026, 10, 26))
        self.assertEqual(s["opened"], 2)
        self.assertEqual(s["resolved"], 2)
        self.assertEqual(s["backlog"], 2)   # tickets 2 and 4
        self.assertEqual(s["net_change"], 0)

    def test_average_days_to_resolve(self):
        s = tr.build_stats(self.tickets, date(2026, 10, 26))
        self.assertAlmostEqual(s["avg_days_to_resolve"], (2 + 7) / 2)

    def test_empty_week(self):
        s = tr.build_stats(self.tickets, date(2026, 9, 1))
        self.assertEqual(s["opened"], 0)
        self.assertIsNone(s["avg_days_to_resolve"])

    def test_report_text_mentions_key_numbers(self):
        s = tr.build_stats(self.tickets, date(2026, 10, 26))
        text = tr.format_report(s, [(5, "bad row")])
        self.assertIn("Tickets opened:      2", text)
        self.assertIn("Skipped 1 row(s)", text)


if __name__ == "__main__":
    unittest.main()
