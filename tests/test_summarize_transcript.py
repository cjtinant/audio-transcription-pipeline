"""Tests for summarize_transcript.py's pure functions.

Run from the repo root:  python3 -m unittest discover tests
No LLM is called — these cover prompts, parsing, formatting, and saving.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from summarize_transcript import (  # noqa: E402
    MEETING_PROMPTS,
    MEETING_TYPE_DESCRIPTIONS,
    _post_with_retry,
    format_transcript,
    get_prompt,
    read_whisperx,
    save_outputs,
)

# Imported as modules too: the speaker-name tests compare the two tools'
# parse_subject implementations against each other, since a divergence
# there would silently break every cache lookup.
import review_transcript  # noqa: E402
import summarize_transcript  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code, retry_after=None):
        self.status_code = status_code
        self.headers = {}
        if retry_after is not None:
            self.headers["retry-after"] = retry_after

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _fake_post_sequence(statuses):
    """Return a fake httpx.post yielding the given statuses in order."""
    responses = [_FakeResponse(*s) if isinstance(s, tuple) else _FakeResponse(s)
                 for s in statuses]
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return responses[len(calls) - 1]

    return fake_post, calls


class TestPostWithRetry(unittest.TestCase):
    def test_success_first_try_no_sleep(self):
        post, calls = _fake_post_sequence([200])
        sleeps = []
        r = _post_with_retry("u", _post=post, _sleep=sleeps.append)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_429_retries_then_succeeds(self):
        # The failure mode that motivated this (2026-07-14): --merge's
        # second back-to-back large request hits a rate limit.
        post, calls = _fake_post_sequence([429, 200])
        sleeps = []
        r = _post_with_retry("u", _post=post, _sleep=sleeps.append)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [60])  # default 429 wait: one TPM window

    def test_retry_after_header_honored_and_capped(self):
        post, _ = _fake_post_sequence([(429, "15"), (429, "999"), 200])
        sleeps = []
        r = _post_with_retry("u", _post=post, _sleep=sleeps.append)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sleeps, [15, 120])  # header used; capped at 120

    def test_exhausted_attempts_raise(self):
        post, calls = _fake_post_sequence([429, 429, 429, 429])
        with self.assertRaises(RuntimeError):
            _post_with_retry("u", max_attempts=4, _post=post,
                             _sleep=lambda s: None)
        self.assertEqual(len(calls), 4)

    def test_client_error_not_retried(self):
        # A 401 (bad key) must fail immediately, not loop for minutes.
        post, calls = _fake_post_sequence([401])
        with self.assertRaises(RuntimeError):
            _post_with_retry("u", _post=post, _sleep=lambda s: None)
        self.assertEqual(len(calls), 1)


class TestGetPrompt(unittest.TestCase):
    def test_known_preset_returns_prompt(self):
        self.assertIn("meeting summarizer", get_prompt("general"))

    def test_custom_requires_prompt(self):
        with self.assertRaises(ValueError):
            get_prompt("custom")

    def test_custom_returns_custom(self):
        self.assertEqual(get_prompt("custom", "My prompt."), "My prompt.")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            get_prompt("karaoke")


class TestPresetConsistency(unittest.TestCase):
    def test_every_prompt_has_a_listed_description(self):
        # Regression for the grant_planning gap (2026-07-12): a preset that
        # exists in MEETING_PROMPTS but not in MEETING_TYPE_DESCRIPTIONS is
        # silently omitted from --list-types.
        missing = set(MEETING_PROMPTS) - set(MEETING_TYPE_DESCRIPTIONS)
        self.assertEqual(missing, set(),
                         f"presets missing from --list-types: {missing}")


class TestReadWhisperx(unittest.TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            read_whisperx("/nonexistent/meeting.json")

    def test_parses_segments_with_defaults(self):
        data = {"segments": [
            {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_00",
             "text": " Hello there. "},
            {"text": "No timing info."},
        ]}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            p.write_text(json.dumps(data))
            segs = read_whisperx(str(p))
        self.assertEqual(segs[0]["text"], "Hello there.")
        self.assertEqual(segs[1]["speaker"], "UNKNOWN")
        self.assertEqual(segs[1]["start"], 0.0)


class TestFormatTranscript(unittest.TestCase):
    def test_speaker_and_time_format(self):
        segs = [{"start": 65.0, "end": 67.0, "speaker": "SPEAKER_01",
                 "text": "Hi."}]
        self.assertEqual(format_transcript(segs), "[SPEAKER_01 @ 65.0s] Hi.")


class TestSaveOutputs(unittest.TestCase):
    def test_json_input_writes_transcript_and_summary(self):
        with tempfile.TemporaryDirectory() as td:
            paths = save_outputs("transcript", "summary",
                                 "meeting.json", output_dir=td)
            self.assertIsNotNone(paths["transcript_path"])
            self.assertTrue(Path(paths["summary_path"]).exists())
            self.assertTrue(Path(paths["transcript_path"]).exists())

    def test_txt_input_skips_transcript_copy(self):
        # A cleaned .txt IS the transcript — copying it back out would just
        # duplicate the input file.
        with tempfile.TemporaryDirectory() as td:
            paths = save_outputs("transcript", "summary",
                                 "meeting_clean.txt", output_dir=td)
            self.assertIsNone(paths["transcript_path"])
            self.assertTrue(Path(paths["summary_path"]).exists())


class TestDefaultOutputDirEnvVar(unittest.TestCase):
    def test_env_var_overrides_default(self):
        # DEFAULT_OUTPUT_DIR is read at import time, so test in a fresh
        # interpreter rather than fighting module caching here.
        result = subprocess.run(
            [sys.executable, "-c",
             "import summarize_transcript as s; print(s.DEFAULT_OUTPUT_DIR)"],
            env={**os.environ, "TRANSCRIBE_OUTPUT_DIR": "/tmp/custom-archive"},
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), "/tmp/custom-archive")

    def test_default_without_env_var(self):
        env = {k: v for k, v in os.environ.items()
               if k != "TRANSCRIBE_OUTPUT_DIR"}
        result = subprocess.run(
            [sys.executable, "-c",
             "import summarize_transcript as s; print(s.DEFAULT_OUTPUT_DIR)"],
            env=env, cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(),
                         "~/PROJECTS/audio-transcription-output")


if __name__ == "__main__":
    unittest.main()


class TestSpeakerNameInjection(unittest.TestCase):
    """
    Approaches 4, 3 and 1 from WATERSHED's speaker-name injection design
    map (2026-07-24). Regression basis: the MEFA run produced summaries
    with no real names at all because nothing resolved SPEAKER_XX.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "One."},
            {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_04", "text": "Two."},
            {"start": 4.0, "end": 6.0, "speaker": "SPEAKER_02", "text": "Three."},
        ]

    def _write(self, name="2026-07-24_MEFA_manuscript-discussion.json",
               cache=None):
        path = Path(self.tmp) / name
        path.write_text(json.dumps({"segments": self.segments}))
        if cache is not None:
            (Path(self.tmp) / ".speaker-cache.json").write_text(
                json.dumps(cache)
            )
        return str(path)

    # ── subject parsing ───────────────────────────────────────────────
    def test_parse_subject_strips_date_and_audio_suffix(self):
        self.assertEqual(
            summarize_transcript.parse_subject("2026-07-07_soil-moisture_audio.json"),
            "soil-moisture",
        )

    def test_parse_subject_strips_model_comparison_suffix(self):
        self.assertEqual(
            summarize_transcript.parse_subject("2026-06-09_tho-meet_large-v3.json"),
            "tho-meet",
        )

    def test_parse_subject_matches_review_tool(self):
        """Both tools must key the cache identically or lookups silently miss."""
        for stem in ("2026-07-07_soil-moisture_audio.json",
                     "2026-06-09_audio_tho-meet.json",
                     "no-convention-here.json"):
            self.assertEqual(
                summarize_transcript.parse_subject(stem),
                review_transcript.parse_subject(Path(stem)),
                f"parse_subject diverged on {stem}",
            )

    # ── approach 4: cache substitution ────────────────────────────────
    def test_cache_names_substituted_into_transcript(self):
        path = self._write(cache={"MEFA_manuscript-discussion":
                                  {"SPEAKER_00": "Jason"}})
        _, transcript = summarize_transcript.prepare_transcript(path)
        self.assertIn("[Jason @ 0.0s]", transcript)

    def test_unnamed_speakers_keep_their_label(self):
        """A wrong name is worse than no name — never blank or guess."""
        path = self._write(cache={"MEFA_manuscript-discussion":
                                  {"SPEAKER_00": "Jason"}})
        _, transcript = summarize_transcript.prepare_transcript(path)
        self.assertIn("SPEAKER_02", transcript)
        self.assertIn("SPEAKER_04", transcript)

    def test_missing_cache_is_not_an_error(self):
        path = self._write()
        _, transcript = summarize_transcript.prepare_transcript(path)
        self.assertIn("SPEAKER_00", transcript)

    def test_corrupt_cache_is_not_an_error(self):
        path = self._write()
        (Path(self.tmp) / ".speaker-cache.json").write_text("{not json")
        self.assertEqual(summarize_transcript.load_speaker_names(path), {})

    def test_explicit_names_override_cache(self):
        path = self._write(cache={"MEFA_manuscript-discussion":
                                  {"SPEAKER_00": "FromCache"}})
        _, transcript = summarize_transcript.prepare_transcript(
            path, speaker_names={"SPEAKER_00": "Explicit"}
        )
        self.assertIn("Explicit", transcript)
        self.assertNotIn("FromCache", transcript)

    def test_use_cache_false_leaves_labels_raw(self):
        path = self._write(cache={"MEFA_manuscript-discussion":
                                  {"SPEAKER_00": "Jason"}})
        _, transcript = summarize_transcript.prepare_transcript(
            path, use_cache=False
        )
        self.assertNotIn("Jason", transcript)

    def test_subject_override_selects_a_different_entry(self):
        path = self._write(cache={"other-subject": {"SPEAKER_00": "Liz"}})
        _, transcript = summarize_transcript.prepare_transcript(
            path, subject="other-subject"
        )
        self.assertIn("[Liz @ 0.0s]", transcript)

    def test_apply_speaker_names_does_not_mutate_input(self):
        """run_pipeline hands segments back to the caller."""
        original = [dict(s) for s in self.segments]
        summarize_transcript.apply_speaker_names(
            self.segments, {"SPEAKER_00": "Jason"}
        )
        self.assertEqual(self.segments, original)

    def test_txt_input_passes_through_untouched(self):
        path = Path(self.tmp) / "cleaned.txt"
        path.write_text("Jason: already named by a human.\n")
        segments, transcript = summarize_transcript.prepare_transcript(str(path))
        self.assertIsNone(segments)
        self.assertIn("already named", transcript)

    # ── pair parsing ──────────────────────────────────────────────────
    def test_parse_speaker_pairs(self):
        self.assertEqual(
            summarize_transcript.parse_speaker_pairs(
                "SPEAKER_00=Jason, SPEAKER_02=Liz"
            ),
            {"SPEAKER_00": "Jason", "SPEAKER_02": "Liz"},
        )

    def test_parse_speaker_pairs_rejects_malformed(self):
        with self.assertRaises(ValueError):
            summarize_transcript.parse_speaker_pairs("SPEAKER_00")

    # ── approaches 3 and 1: prompt construction ───────────────────────
    def test_no_speaker_prompt_by_default(self):
        self.assertEqual(summarize_transcript.build_speaker_prompt(), "")

    def test_roster_prompt_lists_names_and_forbids_others(self):
        p = summarize_transcript.build_speaker_prompt(roster=["Jason", "Liz"])
        self.assertIn("- Jason", p)
        self.assertIn("- Liz", p)
        self.assertIn("ONLY", p)

    def test_infer_prompt_used_when_no_roster(self):
        p = summarize_transcript.build_speaker_prompt(infer=True)
        self.assertIn("(inferred)", p)
        self.assertNotIn("ONLY", p)

    def test_roster_wins_over_infer(self):
        """A closed vocabulary is strictly safer than an open one."""
        p = summarize_transcript.build_speaker_prompt(
            roster=["Jason"], infer=True
        )
        self.assertIn("ONLY", p)

    def test_both_inference_prompts_require_hedging(self):
        """Tier 4: a confidently wrong name is worse than SPEAKER_00."""
        for p in (summarize_transcript.build_speaker_prompt(roster=["Jason"]),
                  summarize_transcript.build_speaker_prompt(infer=True)):
            self.assertIn("(inferred)", p)
            self.assertIn("SPEAKER_XX", p)
