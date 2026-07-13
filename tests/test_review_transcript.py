"""Tests for review_transcript.py's pure functions.

Run from the repo root:  python3 -m unittest discover tests
Standard library only, matching the module under test.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from review_transcript import (  # noqa: E402
    build_flagged_report,
    load_segments,
    load_speaker_cache,
    parse_subject,
    parse_timestamp,
)


class TestParseTimestamp(unittest.TestCase):
    def test_minutes_seconds(self):
        self.assertEqual(parse_timestamp("2:26"), 146.0)

    def test_hours_minutes_seconds(self):
        self.assertEqual(parse_timestamp("1:02:26"), 3746.0)

    def test_plain_seconds(self):
        self.assertEqual(parse_timestamp("90"), 90.0)

    def test_garbage_exits(self):
        with self.assertRaises(SystemExit):
            parse_timestamp("not-a-time")

    def test_too_many_parts_exits(self):
        with self.assertRaises(SystemExit):
            parse_timestamp("1:2:3:4")


class TestParseSubject(unittest.TestCase):
    def test_dated_subject_with_audio_suffix(self):
        self.assertEqual(
            parse_subject(Path("2026-07-07_soil-moisture_audio.json")),
            "soil-moisture",
        )

    def test_dated_audio_prefix_ordering(self):
        self.assertEqual(
            parse_subject(Path("2026-06-09_audio_tho-meet.json")),
            "tho-meet",
        )

    def test_model_comparison_suffix_stripped(self):
        self.assertEqual(
            parse_subject(Path("2026-06-09_audio_tho-meet_large-v3.json")),
            "tho-meet",
        )

    def test_nonconforming_name_falls_back_to_stem(self):
        self.assertEqual(parse_subject(Path("meeting.json")), "meeting")


class TestBuildFlaggedReport(unittest.TestCase):
    def _segment(self, words, start=0.0):
        return {
            "start": start,
            "end": start + 30.0,
            "speaker": "SPEAKER_00",
            "logprob": -0.1,
            "words": words,
        }

    def test_uses_word_level_timestamp_not_segment_start(self):
        # Regression for the 2026-07-12 fix: a word 19s into a segment that
        # starts at 0:00 must report [0:19], not [0:00].
        seg = self._segment(
            [{"w": "late", "s": 0.05, "spk": "SPEAKER_00", "t": 19.0}]
        )
        report = build_flagged_report([seg], threshold=0.2)
        self.assertIn("[0:19]", report)
        self.assertNotIn("[0:00]", report)

    def test_falls_back_to_segment_start_without_alignment(self):
        seg = self._segment(
            [{"w": "word", "s": 0.05, "spk": "SPEAKER_00", "t": None}],
            start=42.0,
        )
        report = build_flagged_report([seg], threshold=0.2)
        self.assertIn("[0:42]", report)

    def test_threshold_filters(self):
        seg = self._segment([
            {"w": "confident", "s": 0.9, "spk": "SPEAKER_00", "t": 1.0},
            {"w": "shaky", "s": 0.1, "spk": "SPEAKER_00", "t": 2.0},
        ])
        report = build_flagged_report([seg], threshold=0.2)
        self.assertIn("'shaky'", report)
        self.assertNotIn("'confident' (confidence", report)

    def test_context_marks_target_word(self):
        seg = self._segment([
            {"w": "one", "s": 0.9, "spk": "SPEAKER_00", "t": 1.0},
            {"w": "two", "s": 0.1, "spk": "SPEAKER_00", "t": 2.0},
            {"w": "three", "s": 0.9, "spk": "SPEAKER_00", "t": 3.0},
        ])
        report = build_flagged_report([seg], threshold=0.2)
        self.assertIn("one **two** three", report)

    def test_nothing_flagged(self):
        seg = self._segment(
            [{"w": "fine", "s": 0.99, "spk": "SPEAKER_00", "t": 1.0}]
        )
        report = build_flagged_report([seg], threshold=0.2)
        self.assertIn("(none found)", report)


class TestLoadSegments(unittest.TestCase):
    def test_parses_whisperx_shape_with_defaults(self):
        data = {
            "segments": [
                {
                    "start": 1.0,
                    "end": 2.5,
                    "speaker": "SPEAKER_01",
                    "avg_logprob": -0.25,
                    "words": [
                        {"word": "hello", "score": 0.98,
                         "speaker": "SPEAKER_01", "start": 1.1},
                        # Unaligned punctuation: no score, no start
                        {"word": "—"},
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.json"
            p.write_text(json.dumps(data))
            segs = load_segments(p)

        self.assertEqual(len(segs), 1)
        words = segs[0]["words"]
        self.assertEqual(words[0]["w"], "hello")
        self.assertEqual(words[0]["t"], 1.1)
        self.assertEqual(words[1]["s"], 1.0)  # missing score defaults high
        self.assertIsNone(words[1]["t"])      # missing start -> None


class TestLoadSpeakerCache(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(load_speaker_cache(Path("/nonexistent/cache.json")), {})

    def test_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cache.json"
            p.write_text("{not json")
            self.assertEqual(load_speaker_cache(p), {})


if __name__ == "__main__":
    unittest.main()
