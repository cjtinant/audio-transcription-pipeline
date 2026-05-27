# Watershed or Parking lot or Issues or whatevs

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

**To resolve:** run both models on a representative sample recording and compare
transcript quality before updating the docs. If `large-v3` is better or neutral,
update all four files and the README. If `large-v2` remains preferable, add a
note to the README explaining the deliberate choice.

**Flagged:** 2026-05-26

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
