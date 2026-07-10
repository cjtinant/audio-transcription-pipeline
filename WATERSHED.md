# Watershed

Next steps, open questions, and unresolved decisions. Move items to a commit or
close them when resolved.

---

## Unresolved Issues

### Friction in Daily Use

1. **Non-standard Naming of Scripts**

**Current:** .venv~/PROJECTS/audio-transcription-pipeline (main) % ls  
00_admin quickstart.md scratch.md transcribe.sh docs README.md
summarize-transcript.py WATERSHED.md output review_transcript.py
summarize-transcript.R

**To Resolve:** Create a naming convention (see below)

2. **Audio File Renaming:** There is too much friction in the current process

**To Resolve:**

1. Identify a standard naming convention and implement automation,
2. Create a default for my primary use case -- Zoom audio recordings

# Quick Start

## Steps

1. **Transcribe**

### Step 1 — Transcribe

<!--
Issue: There is friction typing long names into bash
-->

1. **Copy the path** to the m4a file you want to transcribe using
   `copy pathname` in Finder.

<!--
Issue: Default naming convention in Zoom is bad.
Zoom folder names always contain spaces — always wrap the path in quotes:
**Consider automating rename moving forward**
-->

2. **Rename** folder to: `yyyy-mm-dd_subject-name` and m4a audio file to
   `yyyy-mm-dd_subject-name_audio.m4a`

3. Run the `transcribe` script in `bash`

<!--
Default Zoom folder is in `~/Documents/Zoom/`. This causes issues with
ICloud for me, because I don't always have an internet connection.
So, I moved the Zoom folder to C:
-->

_Example:_ transcribe
"/Users/cjtinant/Zoom/2026-07-07_soil-moisture/2026-07-07_soil-moisture_audio.m4a"
--min_speakers 3 --max_speakers 3

<!--
note: updated output in the script to
`~/audio-transcription-pipeline/output/raw/*_audio.json`
-->

PROJ_ROOT/output/raw/TIMESTAMP-OF-RECORDING.json

- Update nam transcribe.sh output to additionally produce a raw text file
  PROJ_ROOT/output/raw/TIMESTAMP-OF-RECORDING.json

**STEP_02-review-transcript**

- Update input for transcript_review default to
  audio-transcription-pipeline/output/processed/

  audio1391089713.json

- Update output file name for transcribe.R and transcribe.py to
  TIMESTAMP-OF-RECORDING.json
  PROJ_ROOT/output/processed/TIMESTAMP-OF-RECORDING.json

## Parked:

### Spell-check pass on transcript JSON

Add a spell-check flag to `review_transcript.py`, alongside existing
confidence-threshold flagging.

- Walk the `words` array per token (not full sentence text) so punctuation
  doesn't interfere.
- Needs a custom word list layered on the base dictionary — institution/ proper
  nouns (TEA-Center, pyannote, WhisperX, Lakota terms) will otherwise
  false-positive constantly.
- Flags are a signal, not a fix — still requires human review to resolve.
- Candidate tools: R `hunspell` (fits existing R stack) or Python
  `pyspellchecker` / `hunspell` bindings.

Open question: build as a second flag type in the existing review tool, or a
separate pass?

### `--model large-v2` vs `--model large-v3`

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

### pyannote model: `speaker-diarization-3.1` vs `speaker-diarization-community-1`

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

### torchcodec warning on macOS with FFmpeg 8

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

### Diarization std() warning with pinned speaker count

**Status:** parked — cosmetic, does not affect usable output

When `--min_speakers` and `--max_speakers` are both set to 2, pyannote
occasionally hits a segment too short to compute a speaker embedding reliably,
producing a "std(): degrees of freedom is <= 0" warning. Transcript is produced
normally. May result in uncertain speaker labels on very short segments
(silence, crosstalk).

**Flagged:** 2026-05-26

## Speaker types:

Update speakers or post_process?

**Status:** Resolved — handled in `summarize-transcript.py`.

**Closed:** 2026-07-10

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

---

## Resolved / History

Consolidated from `docs/2026-05-26_session-notes.md` (pre-public-release
cleanup pass).

**2026-05-26 — Fish → bash:** Replaced `transcribe.fish` with `transcribe.sh`.
Fish is a personal shell choice; bash/zsh is transferable to other users.

**2026-05-26 — README split:** README had grown to ~1,100 lines and got in
the way during actual transcription work. Split into `README.md` (daily
use), `docs/installation.md` (setup/troubleshooting), and `docs/reference.md`
(R/Python API, meeting types, LLM backends).

**2026-05-26 — docs/noise-reduction.md added:** Generalized from a personal
inbox note; linked from README.

**2026-05-26 — Project instructions established:** Session continuity
convention, WATERSHED.md convention, `docs/` convention, Perplexity
verification step, commit body guidance.

**2026-05-26 — pyannote model, superseded:** Docs were corrected to
`speaker-diarization-3.1` based on Perplexity verification against WhisperX's
GitHub README at the time. Runtime behavior later showed WhisperX actually
defaults to `speaker-diarization-community-1` — see the still-open parked
item above for current status. Noted here so this history entry isn't
mistaken for the current state.

**Bugs resolved (2026-05-26):**

- `transcribe: command not found` — `~/bin` wasn't on PATH. Fixed by adding
  `export PATH="$HOME/bin:$PATH"` to `~/.zshrc`.
- `bad interpreter: No such file or directory` — venv was built at the old
  `~/audio-transcription-pipeline/` path before the repo moved to
  `~/PROJECTS/`. Shebangs are hardcoded at build time; fixed by rebuilding
  the venv with `uv venv` at the new location.
- `ffmpeg: No such file or directory` (path truncated at a space) — Zoom
  folder names contain spaces and the path wasn't quoted. Fixed by always
  wrapping paths in double quotes.
