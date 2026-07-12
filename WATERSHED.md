# Watershed

Next steps, open questions, and unresolved decisions. Move items to a commit or
close them when resolved.

---

## Parked:

### Review tooling ideas — priority order

Ranked by effort-vs-value, with dependencies noted where an idea isn't as
standalone as it first looked. Tier 1 has no real dependencies and is
cheap/safe; later tiers have real prerequisites or open design questions.

---

### [Tier 2] Audio-linked spot-checking for flagged words

**Status:** idea — blocked on a design decision, not started

Probably the highest-value review-tooling change overall — listening to a
flagged word resolves ambiguity a confidence score alone can't ("Anne will
anger" doesn't tell you what was actually said; hearing it might). Every
flagged word has a timestamp, and ffmpeg is already a dependency, so the
clipping itself is straightforward.

**Real dependency found while scoping:** the private archive design
deliberately keeps audio out of the archive — only JSON and derivatives
land there. Nothing currently records, retrievably, where the source
`.m4a` lives once transcription is done. Needs a design decision (store the
source path somewhere, or require it as an explicit argument) before the
ffmpeg-clipping part can be built.

**Flagged:** 2026-07-11

---

### [Tier 2] Cross-model disagreement as a confidence signal

**Status:** idea — blocked on a prerequisite fix, not started

Two independently-run models agreeing is stronger evidence of correctness
than either model's own self-reported confidence. Proven value: the "Anne
will anger" divergence in the large-v2/v3 comparison wasn't flagged by
either model's own confidence score, only by diffing the two against each
other.

**Real costs:** roughly doubles transcription time per recording, every
time, not just once — a recurring cost, not a one-time setup cost. Also
blocked on a small prerequisite: `transcribe.sh` can't currently run a
second model through the wrapper at all, because of the `--model`
argument-order bug found earlier (hardcoded flag comes after `"$@"`, so a
user-supplied override is silently ignored).

**Flagged:** 2026-07-11

---

### [Tier 3] LLM plausibility/sanity pass on transcript text — combine with spell-check

**Status:** idea — not scoped or started

Feed the plain-text transcript through the summarizer's existing LLM,
asking it to flag anything that reads as semantically odd or out of place.
Catches a different error category than acoustic confidence. Scoping this
out reinforced that it shares the same false-positive risk as the
already-parked spell-check idea below (institution-specific terms and
proper nouns getting flagged as "wrong" by something that doesn't know your
vocabulary) — treat as one combined "sanity pass" feature, not two
separate builds.

**Flagged:** 2026-07-11

---

### [Tier 4] Speaker inference from transcript content (LLM pass)

**Status:** idea — speculative, not started

People sometimes address each other by name or self-introduce in
conversation, which an LLM pass over transcript text could use to infer
speaker identity independent of voice matching. Speculative value — no
evidence this pattern is common in these meetings specifically (didn't show
up in the sample diffed during the model comparison). Real risk of
confident misattribution if the LLM guesses wrong.

**Flagged:** 2026-07-11

---

### [Tier 4] Speaker auto-labeling via voice embeddings

**Status:** idea — biggest build of the batch, not started

`whisperx/diarize.py`'s `DiarizationPipeline` can already return speaker
embeddings (`return_embeddings=True`), currently unused. A local library of
known speakers' voice embeddings, matched against each new recording's
`SPEAKER_XX` clusters via cosine similarity, could propose real names
automatically instead of generic labels.

**Tradeoffs:** requires enrollment UX (a name still has to be attached to
an embedding once, per person), a persistent embeddings library, and has a
cold-start problem — no benefit until enough meetings are enrolled. Real
risk, easy to underweight: a *confidently wrong* name is worse than a
generic `SPEAKER_00` placeholder, since a wrong label might not get
double-checked the way an unlabeled one would. Only worth investing in
after speaker-slot caching (Tier 1) shows the simpler approach isn't
enough.

**Flagged:** 2026-07-11

---

### `summarize-transcript.py` filename blocks clean Python import

**Status:** parked — worked around in docs, not fixed at the source

The hyphen in `summarize-transcript.py` makes it an invalid Python module
name — `from summarize-transcript import run_pipeline` is a syntax error.
`docs/reference.md`'s "Interactive / script usage" section now documents an
`importlib.util` workaround (load by file path instead of importing by
name), but the underlying inconsistency is still there: the R script uses
the same hyphenated naming (`summarize-transcript.R`) and that's fine, since
R's `source()` takes a path, not an identifier — this is Python-specific.

**Options:** rename to `summarize_transcript.py` (breaks the matching CLI
examples and README references to the hyphenated name everywhere else, but
makes direct import work naturally); or leave as-is and treat CLI invocation
as the only supported usage pattern, with `importlib` as a documented
fallback for anyone who wants the return value in a script. No decision made
— found while fixing `docs/reference.md`'s stale references, not
investigated further.

**Flagged:** 2026-07-11

---

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

---

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

**2026-07-11 — External private output archive implemented:** The in-repo
`output/raw/` + `output/processed/` structure was a pipeline-stage layout
(raw JSON vs. processed derivatives) that didn't match actual use — a
recurring subject (`soil-moisture`) was being organized by hand into its own
folder inconsistently, and private research transcripts sat in the same
directory tree as this public repo, protected only by `.gitignore` with no
backup or version history.

Replaced with a single external folder, `~/PROJECTS/audio-transcription-output/`:
flat (the `yyyy-mm-dd_subject-name` naming convention already makes files
findable, so no subfolders needed), local-git-only with no remote (version
history without the data ever leaving the machine — not a substitute for
disk-level backup), and permanent (nothing is ever moved out of it by a
script). Two-stage privacy separation: this archive is the private original
record; producing something shareable is a separate, manual, human step
outside the pipeline's scope.

Implemented in six steps: created and git-initialized the archive folder;
repointed `transcribe.sh`'s `--output_dir`; simplified `review_transcript.py`'s
default-output logic (its old `raw/` → `processed/` special case was dead
code once output is flat); repointed both summarizer scripts' `output_dir`
defaults (and fixed a real bug in the Python version — `Path()` doesn't
expand `~` the way bash does, so the old code would have silently written to
a literal `./~/...` folder); rewrote README's How It Works diagram, Why JSON
section, file table, all Step 1/Step 2 examples, and Project Structure
diagram; removed the `output/` folder and its now-irrelevant `.gitignore`
entries from the pipeline repo.

Also fixed along the way, same class of stale-reference bug caught
repeatedly during this pass: `~/Documents/Zoom/` vs. the actual `~/Zoom/`
location (transcribe.sh header comment), `~/audio-transcription-pipeline`
missing the `PROJECTS/` prefix (three places in `docs/installation.md`), and
two leftover references to the pre-rename script name `transcribe.R`
(should be `summarize-transcript.R`).

**2026-07-11 — large-v2 vs large-v3 comparison resolved, large-v3 adopted:**
Two-way comparison run on `2026-06-09_audio_tho-meet.m4a` (25.2 min, 4
speakers). Findings:

- **Speaker labels:** identical between models (diarization is pyannote's
  job, not Whisper's) — expected, confirms model choice doesn't affect this.
- **Hallucination check:** no red flags. Zero segments crossed the
  low-confidence threshold (avg_logprob < -0.5) in either version.
  Consecutive-duplicate-segment counts were low and similar (6 vs 4), and all
  were short natural repeats ("Yep.", "Excellent."), not fabricated looping
  text. `large-v3`'s reputation for hallucinating in silence didn't
  materialize on this recording.
- **Confidence:** `large-v3` modestly better — avg segment logprob -0.125 vs
  -0.312 for `large-v2`; avg word confidence 0.699 vs 0.696.
- **Readability tradeoff:** `large-v3` produced ~30 fewer words overall,
  mostly by dropping short backchannel filler ("Yeah.", "Right.", "So") that
  `large-v2` kept. Cleaner to read; also quietly discards some acknowledgment
  cues.
- **Accuracy:** 84% word-level agreement overall. Two specific divergences
  flagged for audio spot-check but not independently verified: at 2:26,
  `large-v2` produced "and I have eight of" where `large-v3` produced "Anne
  will anger" (possible proper-noun divergence around a name); at 12:37,
  `large-v3` included a full extra sentence ("with... Come back a month
  later, no, I haven't really done anything on this.") not present in
  `large-v2` at all.

**Decision:** adopt `large-v3` as the default. Nothing in the hallucination
check — the original reason for caution — showed up, and confidence metrics
favor `large-v3`. The two flagged timestamps are open questions, not blockers.
Baseline comparison (Zoom's own transcription) remains deferred to a future
meeting, per the revised scope above.

**Implemented same day:** `transcribe.sh`'s hardcoded `--model` flag, and all
example commands in `README.md`, `docs/installation.md`, and
`docs/reference.md`. Two performance claims in `docs/installation.md`
(10–15× realtime on M1 Max; ~3-5x slower on Intel) were measured for
`large-v2` specifically and were not silently carried over — both now note
the figure is `large-v2`'s, not verified for `large-v3`.

While checking `docs/reference.md` for model references, found it had been
missed by two earlier passes entirely: it still shows the pre-rename script
names (`transcribe.R`/`transcribe.py`, should be `summarize-transcript.R`/
`.py`) and every path still points at `output/meeting.json` (the old in-repo
location, not the archive). Only the model flag was fixed here — the rest is
tracked as a separate cleanup task, not folded into this one.

**2026-07-11 — pyannote model mismatch resolved via source inspection, no
token test needed:** Read `whisperx/diarize.py` directly (installed package
source, not just log output): line 101 hardcodes
`model_config = model_name or "pyannote/speaker-diarization-community-1"`.
Since `transcribe.sh` never passes a model override, WhisperX always
requests `community-1` — this is unconditional, not environment-dependent.

Cross-checked `community-1`'s official HuggingFace model card: it's
self-contained, benchmarked *against* `speaker-diarization-3.1` as a
separate "legacy" model, not built on it. Its own setup instructions
require accepting only its own license — no mention of `3.1` or
`segmentation-3.0` as dependencies.

**Resolution:** `docs/installation.md`'s HuggingFace Setup now says to
accept only `pyannote/speaker-diarization-community-1`'s license. The old
instruction (accept both `segmentation-3.0` and `speaker-diarization-3.1`)
asked for licenses this pipeline doesn't actually use.

One caveat kept honest rather than overclaimed: this rules out `3.1` and
`segmentation-3.0` as requirements with high confidence (source code +
official model card), but can't fully rule out some other undocumented
gated sub-component `community-1` might pull in — that would only surface
empirically, via an actual fresh-account test, which wasn't run.

**2026-07-11 — Tier 1 review-tooling changes built (compact flagged-words
report, speaker-slot caching):**

`--report` flag added to `review_transcript.py`: writes a plain-text file
of only words below the confidence threshold, each with timestamp,
speaker, and surrounding context (bold-marked target word) — tested
against `2026-06-09_audio_tho-meet_large-v3.json` (118 words below 0.20),
confirmed context resolves ambiguous flags like the earlier "Anne will
anger" case.

Speaker-slot caching added: subject slug parsed from the filename's
`yyyy-mm-dd_subject-name` convention (override with `--subject`); speaker
names saved via `--save-speakers SPEAKER_00=Name,...` are stored in a
`.speaker-cache.json` file next to the transcript and pre-filled
automatically next time a transcript with the same subject is opened.
Tested end-to-end: saved names for subject `tho-meet`, confirmed the
second run printed the cached names and the generated HTML's embedded
`KNOWN_NAMES` matched.

Both were built and tested in the sandbox against a copy of real
transcript data (not the read-only upload), no changes needed to the
archive folder or existing HTML review flow. No known issues; open
question of whether the caching actually helps in practice is left to
real use, not testable synthetically.
