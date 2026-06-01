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
3. Something known as a baseline -- how to get this??

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

## Speaker types:

Update speakers or post_process?

### In progress

- Created a first draft of `review_transcript.py`
- **Issue** ‘os\* imported but unused Ruff(F401) [Ln 22, Col 8]

**Flagged:** 2026-05-27

## torchcodec broken on PyTorch 2.8.0 (macOS)

**Status:** Non-fatal — pyannote falls back to alternative audio loading.  
**Symptom:** `LC_RPATH` errors for all FFmpeg versions (4–7) at pipeline
startup.  
**Root cause:** torchcodec incompatible with PyTorch 2.8.0; see version table
at  
https://github.com/pytorch/torchcodec?tab=readme-ov-file#installing-torchcodec  
**Risk:** Low for now; could become blocking if fallback loader is removed in a
future pyannote release.  
**Resolution options:** Downgrade PyTorch to a compatible version, or pin
torchcodec to a compatible release.  
**Parked:** 2026-05-28

## In Progress

### Issues being worked on

## Update with Claude

- rename transcribe.R and transcribe.py to --> summarize-transcript.R and
  summarize-transcript.py

### Next Steps

**STEP_01-transcribe**

- Ask Claude why json instead of txt file?
- Update output file name for transcribe.sh to
  PROJ_ROOT/output/raw/TIMESTAMP-OF-RECORDING.json
- Update transcribe.sh output to additionally produce a raw text file
  PROJ_ROOT/output/raw/TIMESTAMP-OF-RECORDING.json

**STEP_02-review-transcript**

- Update input for transcript_review default to
  audio-transcription-pipeline/output/processed/

  audio1391089713.json

- Update output file name for transcribe.R and transcribe.py to
  TIMESTAMP-OF-RECORDING.json
  PROJ_ROOT/output/processed/TIMESTAMP-OF-RECORDING.json

### Next Steps

- check
  osd4crf_weston-edwards-tinant_planning_2026-05-19-esv2-50p-bg-10p-music-10p

#

**Parked:** 2026-05-28
