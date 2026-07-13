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
    format_transcript,
    get_prompt,
    read_whisperx,
    save_outputs,
)


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
