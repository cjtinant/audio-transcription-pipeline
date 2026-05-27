# Watershed

Unresolved decisions and open questions. Move items to a commit or close them
when resolved.

---

## `--model large-v2` vs `--model large-v3`

**Status:** parked — needs testing before changing docs

WhisperX's current README uses `large-v3` as the example model. This repo
documents `large-v2` throughout (README, transcribe.sh, transcribe.py,
transcribe.R).

`large-v3` may offer better accuracy but has known issues with hallucination on
silent or low-speech segments — a common complaint in the WhisperX issue
tracker. `large-v2` is more conservative and well-tested.

**To resolve:** run a 3-way comparison on the same recording:

1. WhisperX `large-v2` (current default)
2. WhisperX `large-v3`
3. Zoom's built-in transcript (already captured 2026-05-26 as baseline)

Compare: proper noun accuracy, speaker label quality, hallucinations in
low-speech segments, and overall readability. If `large-v3` is better or
neutral, update all four files and the README. If `large-v2` remains preferable,
add a note to the README explaining the deliberate choice.

**Flagged:** 2026-05-26

---

## pyannote model: `speaker-diarization-3.1` vs `speaker-diarization-community-1`

**Status:** parked — docs say 3.1, WhisperX actually uses community-1

Perplexity confirmed that WhisperX's GitHub README points to
`pyannote/speaker-diarization-3.1` for HuggingFace license acceptance. The
`docs/installation.md` reflects this.

However, the live `transcribe --help` output and the runtime log both show
WhisperX defaulting to `pyannote/speaker-diarization-community-1`. This means
users need to accept the license for `community-1`, not `3.1`, for the pipeline
to work without a `GatedRepoError`.

**To resolve:** verify which model page(s) actually gate access by testing with
a fresh HuggingFace token that has only accepted one or the other. Update
`docs/installation.md` HuggingFace Setup accordingly.

**Flagged:** 2026-05-26

---

## torchcodec warning on macOS with FFmpeg 8

**Status:** parked — cosmetic, does not affect output

torchcodec expects FFmpeg 4–7; Homebrew installs FFmpeg 8. WhisperX falls back
to subprocess ffmpeg calls and transcription completes normally. The
PYTHONWARNINGS suppression in transcribe.sh doesn't catch it because the warning
category doesn't match exactly.

To fix properly: either pin FFmpeg to version 7 (`brew install ffmpeg@7`) or
find the correct warning filter string. Not worth doing until it causes an
actual problem.

**Flagged:** 2026-05-26

---

## Diarization std() warning with pinned speaker count

**Status:** parked — cosmetic, does not affect usable output

When `--min_speakers` and `--max_speakers` are both set to 2, pyannote
occasionally hits a segment too short to compute a speaker embedding reliably,
producing a "std(): degrees of freedom is <= 0" warning. Transcript is produced
normally. May result in uncertain speaker labels on very short segments
(silence, crosstalk).

**Flagged:** 2026-05-26
