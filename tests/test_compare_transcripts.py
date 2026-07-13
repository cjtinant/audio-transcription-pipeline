"""Tests for compare_transcripts.py's pure functions.

Run from the repo root:  python3 -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compare_transcripts import (  # noqa: E402
    build_diff_report,
    compute_agreement,
    normalize,
    strip_filler,
)


def _words(*tokens, t_start=0.0, step=1.0):
    return [
        {"w": tok, "t": t_start + i * step, "spk": "SPEAKER_00"}
        for i, tok in enumerate(tokens)
    ]


class TestNormalize(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(normalize("Hello,"), "hello")

    def test_keeps_apostrophes(self):
        self.assertEqual(normalize("Don't"), "don't")


class TestStripFiller(unittest.TestCase):
    def test_removes_filler_regardless_of_case_and_punctuation(self):
        words = _words("Um,", "the", "plan", "Yeah.")
        kept = [w["w"] for w in strip_filler(words)]
        self.assertEqual(kept, ["the", "plan"])


class TestComputeAgreement(unittest.TestCase):
    def test_identical_is_100(self):
        a = _words("the", "same", "words")
        pct, equal, total, _ = compute_agreement(a, a)
        self.assertEqual(pct, 100.0)
        self.assertEqual(equal, total)

    def test_single_substitution(self):
        a = _words("we", "meet", "at", "noon")
        b = _words("we", "met", "at", "noon")
        pct, equal, total, _ = compute_agreement(a, b)
        self.assertEqual(equal, 3)
        self.assertEqual(total, 4)
        self.assertEqual(pct, 75.0)


class TestBuildDiffReport(unittest.TestCase):
    def test_reports_replace_with_timestamp_and_labels(self):
        a = _words("we", "meet", "at", "no", "cost", t_start=100.0)
        b = _words("we", "meet", "at", "lacrosse", t_start=100.0)
        report = build_diff_report(a, b, "model-a", "model-b")
        self.assertIn("replace", report)
        self.assertIn("[1:43]", report)  # divergence starts at word t=103
        self.assertIn("model-a: 'no cost'", report)
        self.assertIn("model-b: 'lacrosse'", report)

    def test_filler_only_difference_shows_no_disagreements(self):
        # One side has backchannel the other lacks — raw < 100%, but the
        # content comparison (and the shown list) must treat them as equal.
        a = _words("Yeah.", "the", "plan", "works")
        b = _words("the", "plan", "works")
        report = build_diff_report(a, b, "a", "b")
        self.assertIn("(no disagreements found)", report)
        self.assertIn("Content agreement: 100.0%", report)


if __name__ == "__main__":
    unittest.main()
