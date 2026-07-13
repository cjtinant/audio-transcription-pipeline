"""Tests for sanity_check_transcript.py's pure functions.

Run from the repo root:  python3 -m unittest discover tests
No LLM is called — these cover parsing and timestamp matching only.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanity_check_transcript import (  # noqa: E402
    build_sanity_report,
    load_known_terms,
    locate_phrase,
    parse_flags,
)


class TestLoadKnownTerms(unittest.TestCase):
    def test_filters_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "terms.txt"
            p.write_text("# comment\n\nWhisperX\n  pyannote  \n# another\n")
            self.assertEqual(load_known_terms(p), ["WhisperX", "pyannote"])

    def test_missing_file_returns_empty(self):
        self.assertEqual(load_known_terms(Path("/nonexistent/terms.txt")), [])


class TestParseFlags(unittest.TestCase):
    def test_multiple_blocks(self):
        response = (
            "FLAG: no cost\n"
            "REASON: 'lacrosse' fits the sports context better.\n\n"
            "FLAG: cow patient\n"
            "REASON: likely a garbled technical term.\n"
        )
        flags = parse_flags(response)
        self.assertEqual(len(flags), 2)
        self.assertEqual(flags[0]["phrase"], "no cost")
        self.assertEqual(flags[1]["phrase"], "cow patient")
        self.assertTrue(flags[1]["reason"].startswith("likely"))

    def test_none_found(self):
        self.assertEqual(parse_flags("NONE FOUND"), [])
        self.assertEqual(parse_flags("  none found  "), [])

    def test_preamble_before_first_flag_ignored(self):
        response = (
            "Here are the issues I noticed:\n\n"
            "FLAG: barbs\nREASON: 'varves' fits the climate-proxy context.\n"
        )
        flags = parse_flags(response)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["phrase"], "barbs")

    def test_missing_reason_yields_empty_string(self):
        flags = parse_flags("FLAG: odd phrase\n")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["reason"], "")


class TestLocatePhrase(unittest.TestCase):
    WORDS = [
        {"w": "The", "t": 10.0},
        {"w": "birch", "t": 11.0},
        {"w": "canoe,", "t": 12.0},
        {"w": "slid.", "t": 13.0},
    ]

    def test_exact_match_returns_first_word_time(self):
        self.assertEqual(locate_phrase("birch canoe", self.WORDS), 11.0)

    def test_match_tolerates_case_and_punctuation(self):
        self.assertEqual(locate_phrase("Birch Canoe slid", self.WORDS), 11.0)

    def test_no_match_returns_none(self):
        self.assertIsNone(locate_phrase("plastic kayak", self.WORDS))


class TestBuildSanityReport(unittest.TestCase):
    WORDS = [{"w": "birch", "t": 61.0}, {"w": "canoe", "t": 62.0}]

    def test_located_flag_gets_timestamp(self):
        flags = [{"phrase": "birch canoe", "reason": "test"}]
        report = build_sanity_report(flags, self.WORDS)
        self.assertIn("[1:01]", report)

    def test_unlocated_flag_reported_not_dropped(self):
        flags = [{"phrase": "not in transcript", "reason": "test"}]
        report = build_sanity_report(flags, self.WORDS)
        self.assertIn("?:??", report)
        self.assertIn("could not be matched back to a timestamp", report)

    def test_no_flags(self):
        report = build_sanity_report([], self.WORDS)
        self.assertIn("0 flag(s)", report)


if __name__ == "__main__":
    unittest.main()
