"""Tests for map_speakers.py's pure functions.

Run from the repo root:  python3 -m unittest discover tests
No LLM, no audio, no network — VTT parsing, alignment voting, and the
confidence threshold only.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import map_speakers  # noqa: E402
from compare_transcripts import flatten_words  # noqa: E402

VTT = """WEBVTT

1
00:00:00.000 --> 00:00:04.000
Jason Tinant: alpha bravo charlie delta

2
00:00:04.000 --> 00:00:08.000
Liz Carter: echo foxtrot golf hotel

3
01:02:03.500 --> 01:02:07.500
Jason Tinant: india juliett kilo lima
"""


def _words(speaker, tokens, start=0.0):
    return [
        {"word": tok, "start": start + i, "score": 0.9, "speaker": speaker}
        for i, tok in enumerate(tokens)
    ]


def _segment(speaker, tokens, start=0.0):
    return {
        "start": start,
        "end": start + len(tokens),
        "speaker": speaker,
        "text": " ".join(tokens),
        "words": _words(speaker, tokens, start),
    }


class TestVttParsing(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "meeting.transcript.vtt"
        self.path.write_text(VTT, encoding="utf-8")

    def test_parses_all_cues(self):
        self.assertEqual(len(map_speakers.parse_vtt(self.path)), 3)

    def test_extracts_speaker_from_cue_prefix(self):
        cues = map_speakers.parse_vtt(self.path)
        self.assertEqual(cues[0]["speaker"], "Jason Tinant")
        self.assertEqual(cues[1]["speaker"], "Liz Carter")

    def test_strips_speaker_prefix_from_text(self):
        cues = map_speakers.parse_vtt(self.path)
        self.assertEqual(cues[0]["text"], "alpha bravo charlie delta")

    def test_parses_hour_component(self):
        """Zoom emits H:MM:SS for anything past an hour."""
        cues = map_speakers.parse_vtt(self.path)
        self.assertAlmostEqual(cues[2]["start"], 3723.5, places=2)

    def test_skips_webvtt_header(self):
        for cue in map_speakers.parse_vtt(self.path):
            self.assertNotIn("WEBVTT", cue["text"])

    def test_bom_is_tolerated(self):
        """Zoom writes a UTF-8 BOM; utf-8-sig must absorb it."""
        path = self.tmp / "bom.vtt"
        path.write_text(VTT, encoding="utf-8-sig")
        self.assertEqual(len(map_speakers.parse_vtt(path)), 3)

    def test_cue_without_speaker_prefix_is_unknown(self):
        path = self.tmp / "cc.vtt"
        path.write_text(
            "WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nplain caption text\n",
            encoding="utf-8",
        )
        self.assertEqual(map_speakers.parse_vtt(path)[0]["speaker"], "UNKNOWN")

    def test_sentence_colon_is_not_read_as_a_speaker(self):
        """A long prefix before ':' is prose, not 'Name:'."""
        path = self.tmp / "colon.vtt"
        long_prefix = "so the thing about all of this " * 3
        path.write_text(
            f"WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\n{long_prefix}: yes\n",
            encoding="utf-8",
        )
        self.assertEqual(map_speakers.parse_vtt(path)[0]["speaker"], "UNKNOWN")

    def test_word_timestamps_interpolated_within_cue(self):
        cues = map_speakers.parse_vtt(self.path)
        seg = map_speakers.to_whisperx_shape(cues)["segments"][0]
        starts = [w["start"] for w in seg["words"]]
        self.assertEqual(starts, sorted(starts))
        self.assertGreaterEqual(starts[0], 0.0)
        self.assertLess(starts[-1], 4.0)


class TestVoting(unittest.TestCase):

    def _vote(self, ref_segments, pipe_segments):
        return map_speakers.vote_names(
            flatten_words(map_speakers._segments_from_dict(
                {"segments": ref_segments})),
            flatten_words(map_speakers._segments_from_dict(
                {"segments": pipe_segments})),
        )

    def test_clean_one_to_one_mapping(self):
        ref = [_segment("Jason", ["alpha", "bravo", "charlie"])]
        pipe = [_segment("SPEAKER_00", ["alpha", "bravo", "charlie"])]
        rows = map_speakers.summarize_votes(self._vote(ref, pipe))
        self.assertEqual(rows[0]["label"], "SPEAKER_00")
        self.assertEqual(rows[0]["name"], "Jason")
        self.assertEqual(rows[0]["share"], 100.0)
        self.assertTrue(rows[0]["confident"])

    def test_merged_cluster_is_flagged_not_named(self):
        """The property that makes this safe: split votes self-report."""
        ref = [_segment("Jason", ["alpha", "bravo"]),
               _segment("Liz", ["charlie", "delta"], start=2)]
        pipe = [_segment("SPEAKER_00", ["alpha", "bravo", "charlie", "delta"])]
        rows = map_speakers.summarize_votes(self._vote(ref, pipe))
        self.assertEqual(rows[0]["share"], 50.0)
        self.assertFalse(rows[0]["confident"])

    def test_runners_up_reported(self):
        ref = [_segment("Jason", ["alpha", "bravo"]),
               _segment("Liz", ["charlie", "delta"], start=2)]
        pipe = [_segment("SPEAKER_00", ["alpha", "bravo", "charlie", "delta"])]
        rows = map_speakers.summarize_votes(self._vote(ref, pipe))
        self.assertTrue(rows[0]["runners_up"])

    def test_disagreed_words_do_not_vote(self):
        """Mistranscriptions are skipped rather than casting noisy votes."""
        ref = [_segment("Jason", ["alpha", "bravo", "charlie"])]
        pipe = [_segment("SPEAKER_00", ["alpha", "XXXX", "charlie"])]
        votes = self._vote(ref, pipe)
        self.assertEqual(sum(votes["SPEAKER_00"].values()), 2)

    def test_unknown_reference_speaker_casts_no_vote(self):
        """A .cc.vtt has no names — it must yield nothing, not 'UNKNOWN'."""
        ref = [_segment("UNKNOWN", ["alpha", "bravo"])]
        pipe = [_segment("SPEAKER_00", ["alpha", "bravo"])]
        self.assertEqual(self._vote(ref, pipe), {})

    def test_label_absent_from_reference_gets_no_row(self):
        ref = [_segment("Jason", ["alpha", "bravo"])]
        pipe = [_segment("SPEAKER_00", ["alpha", "bravo"]),
                _segment("SPEAKER_09", ["zulu", "yankee"], start=5)]
        rows = map_speakers.summarize_votes(self._vote(ref, pipe))
        self.assertEqual([r["label"] for r in rows], ["SPEAKER_00"])

    def test_min_share_threshold_is_respected(self):
        ref = [_segment("Jason", ["a", "b", "c", "d", "e", "f", "g", "h", "i"]),
               _segment("Liz", ["j"], start=9)]
        pipe = [_segment("SPEAKER_00",
                         ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])]
        votes = self._vote(ref, pipe)
        self.assertTrue(map_speakers.summarize_votes(votes, 80.0)[0]["confident"])
        self.assertFalse(map_speakers.summarize_votes(votes, 95.0)[0]["confident"])


class TestReferenceLoading(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_loads_vtt_reference(self):
        path = self.tmp / "meeting.transcript.vtt"
        path.write_text(VTT, encoding="utf-8")
        self.assertEqual(len(map_speakers.load_reference(path)), 3)

    def test_loads_json_reference(self):
        path = self.tmp / "converted.json"
        path.write_text(json.dumps(
            {"segments": [_segment("Jason", ["alpha", "bravo"])]}))
        segs = map_speakers.load_reference(path)
        self.assertEqual(segs[0]["speaker"], "Jason")

    def test_empty_vtt_raises(self):
        path = self.tmp / "empty.vtt"
        path.write_text("WEBVTT\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            map_speakers.load_reference(path)


if __name__ == "__main__":
    unittest.main()
