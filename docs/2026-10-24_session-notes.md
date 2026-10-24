# Session notes — 2026-10-24

## Purpose and current priority

Preserve the project status before a planned major refactor. The user has more
pressing work and is deferring implementation. This session records prior chat
history first, then a read-only review of the repository as it exists today.
Only this session note was created; existing changes were left intact. No
refactor, dependency installation, model inference, benchmark, checkpoint
migration, commit, or remote operation was performed.

## Recorded status from prior chats

Sources reviewed in this chat were **Organize repo session note**, **Update
torchcodec setup docs**, and **Run checkpoint upgrade in zsh**. These are
historical reports, not fresh runtime verification.

- The October 4 maintenance review reported **98 passing unit tests** and a
  passing Bash syntax check. It identified stale model defaults, documentation
  organization, installation reproducibility, and wrapper input/output handling
  as follow-ups.
- The user checked and pulled three local Ollama models. Granite
  `granite4.1:30b` stayed at `3f3e5df8a021` (17 GB); Nemotron
  `nemotron3:33b` stayed at `f6d8b7ff496c` (27 GB); Qwen `qwen3.6:35b`
  changed from `07d35212591f` to `a7eb95c53bcf` (23 GB to 22 GB).
  These are October 4 inventory observations, not today's model inventory.
- Summaries of one corrected planning-reflection transcript were compared
  across all three models. Qwen was the preferred editing base for that
  recording. All three introduced unsupported claims or omitted important
  details; this did not establish a general default.
- A tighter first prompt improved proposal framing and reduced invented
  elaborations. Remaining errors included downgrading explicit intentions,
  inventing task/event timing, treating an already scheduled meeting as a new
  scheduling task, and attaching incorrect or weak timestamps.
- Prompt v2 and a sequential comparison runner were prepared. V2 separates
  final decisions from personal intentions, preserves tentative language,
  prohibits inferred timing, and requires supporting source timestamps. The
  last handoff said **v2 inference had not run**. The same source should remain
  fixed for that comparison; a separate recording is needed for confirmation.
- A public-benchmark plan was documented: QMSum for text summarization and
  a separate AMI evaluation for transcription/diarization, with WER, DER,
  real-time factor, and memory measurements. No completed benchmark was
  reported in the reviewed history.
- **No replacement Ollama default was selected.** Choosing and validating one,
  including the sanity-check tool, remained open.
- The later checkpoint chat supplied a command using the repository's Python
  environment. It did not establish that the permanent upgrade succeeded.

The prior handoff's immediate next action was the v2 comparison. The user's
October 24 direction now takes priority: preserve status and defer further work
until there is time to scope the major refactor.

## Repository status observed on October 24

### Git baseline and work in progress

The checkout is on `main`, at `938030a` — `docs: update local summarizer
comparison notes`, dated October 4, 2026, 18:03:58 -06:00. The six most recent
commits are from October 4 and include decoder repair, transcription-review
documentation, and summary-comparison documentation. Remote synchronization was
not checked.

The working tree was already dirty before this note:

| Path | Existing status | Contents/purpose |
| --- | --- | --- |
| `docs/2026-10-04_session-notes.md` | Modified | 20 added lines recording tighter-prompt results and v2 preparation |
| `docs/pipeline-reference.md` | Modified | 62 added lines documenting results, v2 commands, and evaluation criteria |
| `prompts/planning-reflection-v2.txt` | Untracked | Prepared second prompt revision |
| `scripts/compare-planning-prompts.sh` | Untracked | Prepared three-model comparison runner |

These changes agree with the last chat handoff and were preserved. They have
not been committed by this session. This new note is an additional untracked
file until deliberately staged later.

### Structure and implemented workflow

The tracked implementation remains five top-level Python tools, five matching
test modules, and a Bash transcription wrapper. There is no tracked package
manifest such as `pyproject.toml`, no tracked CI workflow, and no `make test`
target. `Makefile` only installs the `transcribe` symlink and marks its target
executable.

| Entry point | Current responsibility |
| --- | --- |
| `transcribe.sh` | Activates the local venv, obtains the Hugging Face token, records source-audio paths, and invokes WhisperX; defaults to large-v3, CPU/int8, English, diarization, and JSON output |
| `review_transcript.py` | Builds HTML review/export pages, flags low-confidence words, maintains speaker-name caches, and clips source audio using FFmpeg |
| `compare_transcripts.py` | Compares normalized words from two transcripts and reports raw/content agreement and disagreements; agreement is not reference accuracy |
| `map_speakers.py` | Transfers speaker names from VTT/JSON reference text using aligned-word votes; supports cache writing and VTT conversion |
| `sanity_check_transcript.py` | Uses an LLM and known vocabulary to flag implausible phrases and locate them in source words |
| `summarize_transcript.py` | Accepts JSON or reviewed text, applies speaker names and prompt presets/custom prompts, calls Anthropic or local Ollama, and supports two-summary merging |

The tools share functions through sibling-module imports. Speaker caches and
source-audio sidecars remain part of the file-based workflow. The shared
`TRANSCRIBE_OUTPUT_DIR` setting defaults to the separate private
`~/PROJECTS/audio-transcription-output` archive. No archive outputs or personal
audio were processed or inventoried in this review.

The v2 runner is present and uses unique output directories, frozen input and
prompt copies, SHA-256 checksums, an Ollama inventory snapshot, model settings,
logs, and timestamps. It runs Qwen, Granite, and Nemotron sequentially and stops
on failure. Its existence does not establish that someone has run it; completion
outside the reviewed repository/history remains unverified.

### Defaults and unresolved behavior

- `summarize_transcript.py` still falls back to
  `llama3.1:8b-instruct-q6_k` for Ollama. Historical records say this model was
  removed. An explicit model or `SUMMARIZE_OLLAMA_MODEL` remains necessary if
  that inventory is unchanged; today's Ollama service was not queried.
- The Anthropic fallback in source is `claude-opus-5`, with 16,000-token
  summary/merge ceilings and environment/CLI overrides. This records source
  configuration only; provider model availability and historical pricing or
  capability claims were not checked.
- The wrapper still reads `$1` and writes the source-audio sidecar before
  WhisperX validates the invocation. It has no explicit early missing-input or
  missing-file validation and does not explicitly stop on activation failure.
- A user `--output_dir` can override WhisperX output while the wrapper's
  sidecar remains in the default/environment-selected archive; this mismatch
  is explicitly acknowledged in the wrapper comments. No wrapper test module
  is tracked.
- The wrapper follows installation symlinks, accepts an exported `HF_TOKEN`
  before its home-file fallback, and places user arguments after defaults.
  Preserve these implemented behaviors when defining a future refactor's
  compatibility requirements.

### Runtime/dependency evidence

Read-only distribution metadata from the existing `.venv` reports:

| Distribution | Installed version |
| --- | --- |
| torch / torchaudio | 2.8.0 / 2.8.0 |
| torchcodec | 0.7.0 |
| av | 14.4.0 |
| whisperx | 3.8.6 |
| faster-whisper | 1.2.1 |
| pyannote.audio | 4.0.4 |
| lightning | 2.6.4 |
| httpx | 0.28.1 |

`requirements-lock.txt` remains a July 12 macOS arm64/Python 3.11 snapshot.
It lists `av==17.0.1`, so it does not match the current installed PyAV metadata.
The installation guide now clearly distinguishes that snapshot from unpinned
fresh installs; the earlier October 4 recommendation to clarify this distinction
has therefore already received documentation work.

The installation guide records an adopted October 4 repair: source-built
PyAV 14.4.0 sharing Homebrew FFmpeg 7 libraries with TorchCodec. It reports
successful decoding and short/long transcription runs without the earlier
loader/duplicate-library warnings. The wrapper now requires Homebrew ffmpeg@7
libraries on macOS and sets `DYLD_LIBRARY_PATH` inside the wrapper. Today's
metadata is consistent with the documented Python-package combination, but no
library load, FFmpeg execution, or end-to-end run was repeated today.

The ignored local `scratch.md`, last modified October 16 according to filesystem
metadata, contains a permanent Lightning checkpoint-upgrade failure: attempted
CUDA deserialization on a machine without CUDA. There is no success record in
that scratch text. The installation guide's optional upgrade command does not
include CPU mapping. This is an unresolved maintenance observation, separate
from the historically successful decoder repair; it does not establish that
normal transcription is broken. No checkpoint was opened or modified today.

### Documentation and local material

`README.md` is about 28 KB and `WATERSHED.md` about 104 KB. WATERSHED still
combines open decisions, historical conversations/results, and resolved work.
Its leading model-selection item still says candidate evaluation is pending,
while the later session/reference records show a limited one-recording
comparison has occurred. General default selection and public benchmarks do
remain pending. Future reconciliation should retain this distinction.

No tracked `TASKS.md` or `docs/README.md` exists. Dated session notes remain
directly under `docs/`, alongside installation, pipeline, review, and noise
reduction guides. The original and v2 planning prompts both exist.

Local `CLAUDE.md` supplies read-only-by-default and no-publishing rules; no
applicable `AGENTS.md` was found in the repository. Local admin, staging,
archive, scratch, temporary scripts, and the venv are ignored. They exist on
disk but are not tracked deliverables and were neither cleaned up nor added.
Preserve or deliberately review local material before a later structural move.

## Verification and limits of this session

- Parsed all five production Python files and five test modules with `ast`
  successfully, using `python -B` to avoid bytecode writes.
- Counted **98 test methods** statically. The unit suite was **not rerun**:
  tests use temporary files, and the user's instruction restricts writes to this
  note. The 98-test passing result above remains historical.
- `bash -n transcribe.sh scripts/compare-planning-prompts.sh` passed.
- `git diff --check` passed before the note was added; final note checks and
  working-tree inspection are recorded by the session's tool output.
- Package versions were read via metadata without importing inference packages.
  No backend/API calls, model downloads, benchmark runs, dependency checks that
  mutate the environment, or runtime repairs were attempted.

This is a repository inventory and continuity record, not a full correctness
audit or evidence that all current external backends work.

## Handoff for the deferred refactor

When work resumes, first reconcile and preserve the existing uncommitted v2
artifacts and establish a fresh executable test/runtime baseline. Then scope
the refactor around the current CLI workflow, shared transcript/speaker data,
private output paths, and environment/model configuration. Carry forward the
open model-selection and evaluation work, wrapper validation/sidecar issues,
runtime snapshot drift, checkpoint-upgrade observation, and documentation
organization as explicit decisions. No refactor design or implementation was
approved or started in this session.
