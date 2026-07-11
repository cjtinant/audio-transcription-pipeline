# Watershed

Next steps, open questions, and unresolved decisions. Move items to a commit or
close them when resolved.

---

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

### torchcodec warnings on macOS (FFmpeg 8 / PyTorch 2.8.0)

**Status:** parked — cosmetic, non-fatal, does not affect output

Two related symptoms from torchcodec's fallback path:

- FFmpeg 8 (Homebrew default) isn't in torchcodec's supported 4–7 range.
  WhisperX falls back to subprocess ffmpeg calls; transcription completes
  normally. The PYTHONWARNINGS suppression in transcribe.sh doesn't catch it
  because the warning category doesn't match exactly.
- torchcodec is also incompatible with PyTorch 2.8.0, producing `LC_RPATH`
  errors at startup for all FFmpeg versions (4–7). pyannote falls back to an
  alternative audio loader. See the version table at
  https://github.com/pytorch/torchcodec?tab=readme-ov-file#installing-torchcodec

**Risk:** Low for now — could become blocking if the fallback loader is
removed in a future pyannote release.

**Resolution options:** Pin FFmpeg to version 7 (`brew install ffmpeg@7`),
downgrade PyTorch to a compatible version, or pin torchcodec to a compatible
release. Not worth doing until it causes an actual problem.

**Flagged:** 2026-05-26 (FFmpeg 8); 2026-05-28 (PyTorch 2.8.0)

---

### Diarization std() warning with pinned speaker count

**Status:** parked — cosmetic, does not affect usable output

When `--min_speakers` and `--max_speakers` are both set to 2, pyannote
occasionally hits a segment too short to compute a speaker embedding reliably,
producing a "std(): degrees of freedom is <= 0" warning. Transcript is produced
normally. May result in uncertain speaker labels on very short segments
(silence, crosstalk).

**Flagged:** 2026-05-26

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

**2026-05-27 — Ruff F401 fixed:** Unused `import os` in `review_transcript.py`
removed (no `os.*` calls anywhere in the file).

**2026-07-10 — Speaker types question closed:** "Update speakers or
post_process?" resolved — handled in `summarize-transcript.py`.

**2026-07-10 — Naming convention formalized:** Adopted
`yyyy-mm-dd_subject-name` (folder and audio file) as the standing convention.
Documented in README with the actual Zoom Copy-Pathname-then-rename workflow.
Because WhisperX and the summarizer scripts both carry the input basename
forward, this single rename is sufficient to get consistent dated names on
the raw JSON, cleaned transcript, and summary — no separate output-naming
logic was needed. Dropped two now-superseded asks from the old Quick Start
notes: producing an extra raw `.txt` from transcribe.sh (conflicts with
JSON-as-source-of-truth design) and pointing `review_transcript.py`'s default
input at `output/processed/` (it correctly takes `output/raw/*.json`).

**2026-05-2x — Zoom recordings folder moved off iCloud:** Zoom's default save
location, `~/Documents/Zoom/`, is iCloud-synced and caused access problems
without an internet connection. Recordings folder relocated to `~/Zoom/`.
README's Zoom instructions should point here, not the Documents default.

**2026-07-10 — torchcodec entries merged:** The FFmpeg 8 warning and the
PyTorch 2.8.0 `LC_RPATH` breakage were two separate parked entries describing
related fallback behavior; merged into one under Parked.
