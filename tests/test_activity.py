import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import activity  # noqa: E402

D = dt.date


def days_from(start, counts):
    return {start + dt.timedelta(i): c for i, c in enumerate(counts)}


class ComputeTests(unittest.TestCase):
    def test_current_streak_includes_today(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 24), [1, 0, 2, 3, 1]), today)
        self.assertEqual(s["current"], (3, D(2026, 10, 26), today))

    def test_current_streak_survives_empty_today(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 24), [0, 1, 1, 4, 0]), today)
        self.assertEqual(s["current"], (3, D(2026, 10, 25), D(2026, 10, 27)))

    def test_current_streak_broken_when_yesterday_empty(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 24), [5, 5, 5, 0, 0]), today)
        self.assertEqual(s["current"], (0, None, None))
        self.assertEqual(s["longest"], (3, D(2026, 10, 24), D(2026, 10, 26)))

    def test_missing_days_count_as_zero(self):
        today = D(2026, 10, 28)
        days = {D(2026, 10, 20): 1, D(2026, 10, 21): 1, D(2026, 10, 27): 1, D(2026, 10, 28): 1}
        s = activity.compute(days, today)
        self.assertEqual(s["current"], (2, D(2026, 10, 27), today))
        self.assertEqual(s["total"], 4)

    def test_streak_across_year_boundary(self):
        today = D(2026, 1, 3)
        s = activity.compute(days_from(D(2025, 12, 29), [0, 1, 1, 1, 1, 1]), today)
        self.assertEqual(s["current"], (5, D(2025, 12, 30), today))
        self.assertEqual(s["longest"], (5, D(2025, 12, 30), today))

    def test_longest_tie_prefers_most_recent(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 20), [1, 1, 0, 0, 1, 1, 0, 0, 0]), today)
        self.assertEqual(s["longest"], (2, D(2026, 10, 24), D(2026, 10, 25)))

    def test_all_empty_period(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 1), [0] * 28), today)
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["current"], (0, None, None))
        self.assertEqual(s["longest"], (0, None, None))
        self.assertIsNone(s["first_contribution"])

    def test_last_year_window_is_365_days(self):
        today = D(2026, 10, 28)
        days = {today - dt.timedelta(days=364): 2, today - dt.timedelta(days=365): 7, today: 1}
        s = activity.compute(days, today)
        self.assertEqual(s["last_year"], 3)
        self.assertEqual(s["total"], 10)

    def test_weekly_buckets_sum_to_last_364_days(self):
        today = D(2026, 10, 28)
        days = {today - dt.timedelta(days=i): 1 for i in range(400)}
        s = activity.compute(days, today)
        self.assertEqual(len(s["weekly"]), 52)
        self.assertEqual(sum(s["weekly"]), 364)


class RenderTests(unittest.TestCase):
    def test_cards_render_and_escape(self):
        today = D(2026, 10, 28)
        s = activity.compute(days_from(D(2026, 10, 1), [1] * 28), today)
        for svg in (activity.stats_card(s, "a&b"), activity.streak_card(s, "a&b")):
            self.assertIn("a&amp;b", svg)
            self.assertTrue(svg.startswith("<svg"))

    def test_range_formatting(self):
        self.assertEqual(activity.fmt_range(D(2026, 1, 1), D(2026, 1, 1)), "Jan 1, 2026")
        self.assertEqual(activity.fmt_range(D(2026, 1, 1), D(2026, 1, 5)), "Jan 1 – Jan 5, 2026")
        self.assertEqual(activity.fmt_range(D(2025, 12, 30), D(2026, 1, 2)), "Dec 30, 2025 – Jan 2, 2026")
        self.assertEqual(activity.fmt_range(None, None), "no active streak")


class AtomicWriteTests(unittest.TestCase):
    def test_failure_keeps_previous_files(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "stats.svg")
            with open(path, "w") as fh:
                fh.write("old")
            files = {"stats.svg": "new", "streak.svg": None}  # None makes the second write fail
            with self.assertRaises(TypeError):
                activity.write_atomic(files, d)
            with open(path) as fh:
                self.assertEqual(fh.read(), "old")
            self.assertEqual(sorted(os.listdir(d)), ["stats.svg"])

    def test_missing_token_exits_nonzero(self):
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            self.assertEqual(activity.main(["--user", "x", "--out", tempfile.gettempdir()]), 2)
        finally:
            if old is not None:
                os.environ["GITHUB_TOKEN"] = old


if __name__ == "__main__":
    unittest.main()
