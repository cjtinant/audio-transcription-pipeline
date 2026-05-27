# Session Notes — 2026-05-26

## Goal

Prepare private `audio-transcription-pipeline` repo for public release.

---

## Key decisions

**Fish → bash** Replaced `transcribe.fish` with `transcribe.sh`. Fish is
personal; bash/zsh is transferable. All fish references removed from README.

**README split** README was ~1,100 lines and getting in the way during actual
use. Split into:

- `README.md` — intro, daily use, checklist (~220 lines)
- `docs/installation.md` — security, platform setup, HuggingFace, testing,
  troubleshooting
- `docs/reference.md` — R/Python API, meeting types, LLM backends

Trigger: got lost in the README while trying to transcribe a file.

**`docs/noise-reduction.md`** Added from
`00_admin/_inbox/noise_reduction_options.md`. Generalized personal references
(Adobe CC subscription, "already installed"). Linked from README.

**`00_admin/` dropped** Served its purpose during cleanup; now empty. Removed
from repo entirely.

**pyannote URL corrected** `speaker-diarization-community-1` →
`speaker-diarization-3.1` in `docs/installation.md` HuggingFace Setup, based on
Perplexity verification against current WhisperX GitHub README.

**Project instructions updated** Added: session continuity section,
encouragement on substantive progress, WATERSHED.md convention, `docs/`
convention, Perplexity verification step, commit body guidance. Removed stale
`00_admin/` reference.

---

## Perplexity queries run

**Query:** What are the current HuggingFace model pages that require license
acceptance for WhisperX with speaker diarization using pyannote? **Result:**
`pyannote/speaker-diarization-3.1` + `pyannote/segmentation-3.0` confirmed from
WhisperX GitHub README. Updated `docs/installation.md`.

**Query:** What is the current recommended way to install Ollama for use with
Python or R inside WSL2? **Result:** Install inside WSL2 Ubuntu, not Windows
host. Connect at `http://localhost:11434`. Use `OLLAMA_HOST=0.0.0.0:11434` if
localhost unreachable. Updated `docs/reference.md` LLM Backend Options.

---

## Files trashed

- `00_admin/_delete/README.md`, `README copy.md`,
  `audio-transcription-pipeline.zip`
- `00_admin/_delete/transcribe.fish`, `transcribe.fish copy`
- `00_admin/_inbox/AI_make-audio-to-transcript.md` — early research notes,
  superseded
- `00_admin/_inbox/voice-text_zoom-recording-blackhole_2026-04-17.md` —
  BlackHole passthru never worked
- `audio-transcription_SETUP copy.md` — single-user draft, content absorbed
- `HERVE_SETUP.md` — single-user draft, content absorbed

---

## Bugs hit and resolved

**`transcribe: command not found`** `~/bin` not on PATH. Fixed by adding
`export PATH="$HOME/bin:$PATH"` to `~/.zshrc` and running `source ~/.zshrc`.
Added `source ~/.zshrc` step and `>>` vs `>` warning to `docs/installation.md`.

**`bad interpreter: No such file or directory`** venv built at old path
(`~/audio-transcription-pipeline/`) before repo was moved to `~/PROJECTS/`.
Shebangs inside venv binaries are hardcoded at build time. Fix: rebuild venv
with `uv venv` in the new location. Added path warning to
`docs/installation.md`.

**`ffmpeg: No such file or directory` (path truncated at space)** Zoom folder
names contain spaces. Path was not quoted. Fix: always wrap paths in double
quotes. Already documented in README and `transcribe.sh` header.

---

## Parked in WATERSHED.md

- `large-v2` vs `large-v3` — needs comparative test before changing docs
- pyannote model discrepancy — `speaker-diarization-3.1` in docs but runtime
  shows `community-1`; needs fresh-token test to confirm which gate matters
- torchcodec warning — FFmpeg 8 incompatibility, cosmetic, not worth fixing yet
- Diarization std() warning — cosmetic with pinned speaker count, output
  unaffected

---

## End state

```
audio-transcription-pipeline/
├── docs/
│   ├── installation.md
│   ├── noise-reduction.md
│   └── reference.md
├── output/
│   └── .gitkeep
├── README.md
├── transcribe.py
├── transcribe.R
├── transcribe.sh
└── WATERSHED.md
```

Repo not yet made public — pending first successful end-to-end transcription run
and review of output quality.
