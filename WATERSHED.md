# Watershed

Next steps, open questions, and unresolved decisions. Move items to a commit or
close them when resolved.

---

## Parked:

### Make the installed `transcribe` wrapper easy to keep in sync

**Status:** idea — not scoped or started

Raised 2026-07-12 as the concrete next step after "confidence in output"
work (Tier 2/3) wrapped up — of the original three friction points (output
confidence, confusing file management, too many manual steps), this is
aimed at the last one.

A related item was dropped earlier the same day (see Resolved/History):
`~/bin/transcribe` had genuinely drifted from the repo's `transcribe.sh`
(missing the sidecar block, stale model/output-dir defaults), but that
specific confusion turned out to be caused by a direct `whisperx`
invocation, not the drift — so nothing was built. The underlying gap is
still real, though: editing `transcribe.sh` doesn't do anything until
someone remembers to run `cp transcribe.sh ~/bin/transcribe`, and today's
priority (easy to update) is a different, better reason to revisit it than
the reason it got dropped for.

**Candidate approaches, not evaluated yet** (carried over from the dropped
item): a Makefile/install-script target for the re-copy step; a symlink
(`ln -s`) instead of a copy, so edits take effect immediately with no
re-sync step — the previously-dropped item noted the install docs' choice
of copy-over-symlink isn't explained anywhere, worth checking if there was
a real reason; or a version/date check `transcribe` prints on startup so
drift is visible immediately if a symlink isn't used.

**Flagged:** 2026-07-12

---

### Review tooling ideas — priority order

Ranked by effort-vs-value, with dependencies noted where an idea isn't as
standalone as it first looked. Tier 1 has no real dependencies and is
cheap/safe; later tiers have real prerequisites or open design questions.

---

### [Tier 3] LLM plausibility/sanity pass on transcript text — combine with spell-check

**Status:** in progress — picked up 2026-07-12 as the direct next step after
Tier 2's noise-reduction ceiling (see Resolved/History)

Feed the plain-text transcript through the summarizer's existing LLM, asking it
to flag anything that reads as semantically odd or out of place. Catches a
different error category than acoustic confidence. Scoping this out reinforced
that it shares the same false-positive risk as the already-parked spell-check
idea below (institution-specific terms and proper nouns getting flagged as
"wrong" by something that doesn't know your vocabulary) — treat as one combined
"sanity pass" feature, not two separate builds.

**Why now:** `compare_transcripts.py` (Tier 2) hit a real ceiling — a
hand-maintained filler-word list only cut disagreements 164 → 124 before
running into the same false-positive risk this item already flagged. Getting
further requires actual judgment about "is this divergence/word substantive,"
not more word-list rules — which is exactly what this item is.

**Skeleton built (2026-07-12), real LLM validation still needed:**
`sanity_check_transcript.py` reuses `summarize-transcript.py`'s
`summarize_anthropic`/`summarize_ollama` for the LLM call itself (loaded via
`importlib` — the hyphenated filename issue below applies here too, worked
around rather than fixed as part of this task) and `review_transcript.py`'s
`load_segments` for parsing. A prompt asks the model to flag phrases that
read as semantically odd, supplying a `known-terms.txt` list (seeded with
TEA-Center, WhisperX, pyannote, OLC/Oglala Lakota College, Lakota — almost
certainly incomplete) so legitimate vocabulary isn't flagged as error, per
the false-positive risk already identified below. Output format is a simple
`FLAG:`/`REASON:` block per flag (chosen over JSON — more forgiving to
parse if a smaller local model doesn't format strictly), matched back to a
timestamp by locating the phrase in the transcript's word list.

Unit-tested what can be tested without a real model: known-terms file
parsing (comments/blanks filtered), flag-block parsing (multiple flags,
`NONE FOUND`, a phrase that doesn't match verbatim — reported as `?:??`
rather than silently dropped or crashing), and confirmed the `importlib`
reuse of `summarize-transcript.py`'s functions actually resolves. The one
thing that can't be verified without your machine: whether the prompt
actually gets good results from a real model, and whether Ollama's
smaller local models follow the `FLAG:`/`REASON:` format reliably or need
a stricter/looser parser.

**Real test run (2026-07-12), both engines, against
`2026-06-09_audio_tho-meet_large-v3.json`:** meaningful quality gap between
engines, not just a style difference.

`ollama` (`llama3.1:8b-instruct-q6_k`): 7 flags, 1 couldn't be matched back
to a timestamp (the model paraphrased instead of quoting verbatim, despite
the prompt's explicit instruction — a real prompt-compliance gap for the
smaller model). Several flags look like informal-speech false positives
despite being told not to flag those ("Not fine.", "And actually what
we'll do is about this."). One genuinely good catch not found by the other
engine or by `compare_transcripts.py`: `[24:21]` flagged garbled grammar
("I haven't done a darn thing since like, I think it's all it is") and
suggested a plausible real reading.

`anthropic` (`claude-sonnet-4-6`): 6 flags, all matched verbatim — no
format-compliance issue. More striking: most of Claude's flags land on
timestamps `compare_transcripts.py` had already found suspicious, from a
completely different signal (semantic plausibility vs. cross-model
disagreement):

- `[20:58]` "lacrosse" ↔ Tier 2's `[20:59] replace: 'no cost' → 'lacrosse'` — exact match.
- `[19:29]` "green" ↔ Tier 2's `[19:30] insert: 'green'` — exact match.
- `[9:14]`/`[9:17]` "Wall Street"/"Causes" ↔ Tier 2's `[9:15] replace: "OLC... Because it's" → "the Wall Street... Causes"` — same region.
- `[7:24]` "Tho" ↔ Tier 2's `[7:24] replace: 'though' → 'Tho'` — same divergence, different theory (Claude guessed a mistranscribed proper name; could equally be the reverse — `2026-06-09_audio_tho-meet`'s own filename already uses "tho" as a subject slug, so `large-v3`'s "Tho" might be the *correct* one and `large-v2`'s "though" the error. Neither tool says which side is right, same as `compare_transcripts.py`'s own design — human judgment still required.)
- `[11:04]` "Nike" is *near* Tier 2's `[11:04] replace: 'Gabe at' → 'the agent of'` but "Nike" itself doesn't appear in that diff — meaning it's possibly a word both models transcribed *identically wrong*, which cross-model diffing structurally cannot see. Genuinely interesting if true, but unconfirmed — would need the raw JSON words checked directly, not done here.

**Decision (2026-07-12):** the two engines are not actually interchangeable
— this test is evidence they never were, the pipeline's docs just treated
them that way. `anthropic` (Claude) becomes the default engine pipeline-wide,
not just for this tool. `ollama` stays fully supported, reframed as the
explicit local/privacy-focused option rather than the default — a real
choice for sensitive recordings, not a downgrade path.

**Rollout completed (2026-07-12):** default engine flipped consistently
across code and docs. Code: `summarize-transcript.py`'s `run_pipeline`/
`run_pipeline_merged`/CLI default, `summarize-transcript.R`'s `match.arg()`
vectors reordered (R uses the first listed value as the default —
confirmed by R semantics, not executed since R isn't available in this
session, worth a quick real check), `sanity_check_transcript.py`'s CLI
default. Docs: `README.md`, `docs/reference.md`, `docs/installation.md` —
every example and section label reordered to present Anthropic first/as
default, Ollama reframed as the local/private option, not a fallback.

One thing caught and fixed along the way, not just relabeled: README's
privacy framing ("your audio and transcripts never have to leave your
computer") was accurate when Ollama was default but became a real
inaccuracy once Anthropic is default — transcript *text* now leaves the
machine unless a user explicitly opts into `--engine ollama`. Rewrote to
distinguish audio (always local) from transcript text (sent externally
only under the default engine) rather than just swapping which option is
labeled "(default)".

**First precision test on unseen content (2026-07-12):** ran
`sanity_check_transcript.py` (Anthropic, default) against
`2026-06-09_audio_mentor-meet.json` — untouched by any tool built this
session, unlike `tho-meet` which had been picked apart repeatedly. 5 flags,
scored against the user's own knowledge of what was actually said:

- **1 confirmed exact catch:** `[14:36]` "barbs" → correct answer "varves"
  (tree-ring/climate-proxy discussion). Claude didn't just find a real
  error, it supplied the right fix.
- **2 likely real catches, context confirmed but exact wording not
  verified:** `[5:53]` "cow patient" (confirmed as garbled mesonet-station
  discussion) and `[14:00]` "save your million" (confirmed as the Dakota
  blizzard discussion).
- **2 false positives:** `[1:50]` "plumber" and `[33:35]` "straight and to
  the right" were both actually said — Claude flagged genuine, correct
  colloquial phrasing about a person's character as semantically odd.
  Different failure mode than Ollama's informal-speech false positives
  from the earlier test (filler/backchannel) — this is unusual-but-real
  descriptive language, not filler.

**Rough precision: 3/5 real, 2/5 false positive** on a single unseen
recording — not a large enough sample to treat as a stable rate, but the
first real signal beyond the `tho-meet` test (which validated
corroboration with `compare_transcripts.py`, not raw precision). Consistent
with "flags are a signal, not a fix" — about 2 in 5 flags being dead ends
here is a real cost of using this tool, not a defect to chase down
immediately.

**Flagged:** 2026-07-11

---

### [Tier 4] Speaker inference from transcript content (LLM pass)

**Status:** idea — speculative, not started

People sometimes address each other by name or self-introduce in conversation,
which an LLM pass over transcript text could use to infer speaker identity
independent of voice matching. Speculative value — no evidence this pattern is
common in these meetings specifically (didn't show up in the sample diffed
during the model comparison). Real risk of confident misattribution if the LLM
guesses wrong.

**Flagged:** 2026-07-11

---

### [Tier 4] Speaker auto-labeling via voice embeddings

**Status:** idea — biggest build of the batch, not started

`whisperx/diarize.py`'s `DiarizationPipeline` can already return speaker
embeddings (`return_embeddings=True`), currently unused. A local library of
known speakers' voice embeddings, matched against each new recording's
`SPEAKER_XX` clusters via cosine similarity, could propose real names
automatically instead of generic labels.

**Tradeoffs:** requires enrollment UX (a name still has to be attached to an
embedding once, per person), a persistent embeddings library, and has a
cold-start problem — no benefit until enough meetings are enrolled. Real risk,
easy to underweight: a _confidently wrong_ name is worse than a generic
`SPEAKER_00` placeholder, since a wrong label might not get double-checked the
way an unlabeled one would. Only worth investing in after speaker-slot caching
(Tier 1) shows the simpler approach isn't enough.

**Flagged:** 2026-07-11

---

### `summarize-transcript.py` filename blocks clean Python import

**Status:** parked — worked around in docs, not fixed at the source

The hyphen in `summarize-transcript.py` makes it an invalid Python module name —
`from summarize-transcript import run_pipeline` is a syntax error.
`docs/reference.md`'s "Interactive / script usage" section documents an
`importlib.util` workaround (load by file path instead of importing by name),
but the underlying inconsistency is still there.

**Update (2026-07-12):** no longer just a documented inconvenience —
`sanity_check_transcript.py` now depends on this same workaround to reach
`summarize_anthropic`/`summarize_ollama` (R is gone as of today, so the old
"R uses the same hyphenated naming and that's fine" comparison no longer
applies either — this is now purely a Python problem with one real
consumer depending on the workaround, not zero).

**Options:** rename to `summarize_transcript.py` (breaks the matching CLI
examples and README references to the hyphenated name everywhere else, but makes
direct import work naturally); or leave as-is and treat CLI invocation as the
only supported usage pattern, with `importlib` as a documented fallback for
anyone who wants the return value in a script. No decision made — found while
fixing `docs/reference.md`'s stale references, not investigated further.

**Flagged:** 2026-07-11

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

**Risk:** Low for now — could become blocking if the fallback loader is removed
in a future pyannote release.

**Resolution options:** Pin FFmpeg to version 7 (`brew install ffmpeg@7`),
downgrade PyTorch to a compatible version, or pin torchcodec to a compatible
release. Not worth doing until it causes an actual problem.

**Flagged:** 2026-05-26 (FFmpeg 8); 2026-05-28 (PyTorch 2.8.0)

---

### Diarization std() warning

**Status:** parked — cosmetic, does not affect usable output

Pyannote occasionally hits a segment too short to compute a speaker embedding
reliably, producing a "std(): degrees of freedom is <= 0" warning. Transcript
is produced normally. May result in uncertain speaker labels on very short
segments (silence, crosstalk).

**Correction (2026-07-12):** originally attributed specifically to pinning
`--min_speakers`/`--max_speakers` to 2. A 2026-07-12 test run (plain
`transcribe`, no speaker-count flags set) produced the same warning —
the cause is broader than pinned speaker count, likely just short/ambiguous
segments generally. Title and description corrected; still cosmetic, still
not worth fixing until it causes an actual problem.

**Flagged:** 2026-05-26

---

## Resolved / History

Consolidated from `docs/2026-05-26_session-notes.md` (pre-public-release cleanup
pass).

**2026-05-26 — Fish → bash:** Replaced `transcribe.fish` with `transcribe.sh`.
Fish is a personal shell choice; bash/zsh is transferable to other users.

**2026-05-26 — README split:** README had grown to ~1,100 lines and got in the
way during actual transcription work. Split into `README.md` (daily use),
`docs/installation.md` (setup/troubleshooting), and `docs/reference.md`
(R/Python API, meeting types, LLM backends).

**2026-05-26 — docs/noise-reduction.md added:** Generalized from a personal
inbox note; linked from README.

**2026-05-26 — Project instructions established:** Session continuity
convention, WATERSHED.md convention, `docs/` convention, Perplexity verification
step, commit body guidance.

**2026-05-26 — pyannote model, superseded:** Docs were corrected to
`speaker-diarization-3.1` based on Perplexity verification against WhisperX's
GitHub README at the time. Runtime behavior later showed WhisperX actually
defaults to `speaker-diarization-community-1` — see the still-open parked item
above for current status. Noted here so this history entry isn't mistaken for
the current state.

**Bugs resolved (2026-05-26):**

- `transcribe: command not found` — `~/bin` wasn't on PATH. Fixed by adding
  `export PATH="$HOME/bin:$PATH"` to `~/.zshrc`.
- `bad interpreter: No such file or directory` — venv was built at the old
  `~/audio-transcription-pipeline/` path before the repo moved to `~/PROJECTS/`.
  Shebangs are hardcoded at build time; fixed by rebuilding the venv with
  `uv venv` at the new location.
- `ffmpeg: No such file or directory` (path truncated at a space) — Zoom folder
  names contain spaces and the path wasn't quoted. Fixed by always wrapping
  paths in double quotes.

**2026-05-27 — Ruff F401 fixed:** Unused `import os` in `review_transcript.py`
removed (no `os.*` calls anywhere in the file).

**2026-07-10 — Speaker types question closed:** "Update speakers or
post_process?" resolved — handled in `summarize-transcript.py`.

**2026-07-10 — Naming convention formalized:** Adopted `yyyy-mm-dd_subject-name`
(folder and audio file) as the standing convention. Documented in README with
the actual Zoom Copy-Pathname-then-rename workflow. Because WhisperX and the
summarizer scripts both carry the input basename forward, this single rename is
sufficient to get consistent dated names on the raw JSON, cleaned transcript,
and summary — no separate output-naming logic was needed. Dropped two
now-superseded asks from the old Quick Start notes: producing an extra raw
`.txt` from transcribe.sh (conflicts with JSON-as-source-of-truth design) and
pointing `review_transcript.py`'s default input at `output/processed/` (it
correctly takes `output/raw/*.json`).

**2026-05-2x — Zoom recordings folder moved off iCloud:** Zoom's default save
location, `~/Documents/Zoom/`, is iCloud-synced and caused access problems
without an internet connection. Recordings folder relocated to `~/Zoom/`.
README's Zoom instructions should point here, not the Documents default.

**2026-07-10 — torchcodec entries merged:** The FFmpeg 8 warning and the PyTorch
2.8.0 `LC_RPATH` breakage were two separate parked entries describing related
fallback behavior; merged into one under Parked.

**2026-07-11 — External private output archive implemented:** The in-repo
`output/raw/` + `output/processed/` structure was a pipeline-stage layout (raw
JSON vs. processed derivatives) that didn't match actual use — a recurring
subject (`soil-moisture`) was being organized by hand into its own folder
inconsistently, and private research transcripts sat in the same directory tree
as this public repo, protected only by `.gitignore` with no backup or version
history.

Replaced with a single external folder,
`~/PROJECTS/audio-transcription-output/`: flat (the `yyyy-mm-dd_subject-name`
naming convention already makes files findable, so no subfolders needed),
local-git-only with no remote (version history without the data ever leaving the
machine — not a substitute for disk-level backup), and permanent (nothing is
ever moved out of it by a script). Two-stage privacy separation: this archive is
the private original record; producing something shareable is a separate,
manual, human step outside the pipeline's scope.

Implemented in six steps: created and git-initialized the archive folder;
repointed `transcribe.sh`'s `--output_dir`; simplified `review_transcript.py`'s
default-output logic (its old `raw/` → `processed/` special case was dead code
once output is flat); repointed both summarizer scripts' `output_dir` defaults
(and fixed a real bug in the Python version — `Path()` doesn't expand `~` the
way bash does, so the old code would have silently written to a literal
`./~/...` folder); rewrote README's How It Works diagram, Why JSON section, file
table, all Step 1/Step 2 examples, and Project Structure diagram; removed the
`output/` folder and its now-irrelevant `.gitignore` entries from the pipeline
repo.

Also fixed along the way, same class of stale-reference bug caught repeatedly
during this pass: `~/Documents/Zoom/` vs. the actual `~/Zoom/` location
(transcribe.sh header comment), `~/audio-transcription-pipeline` missing the
`PROJECTS/` prefix (three places in `docs/installation.md`), and two leftover
references to the pre-rename script name `transcribe.R` (should be
`summarize-transcript.R`).

**2026-07-11 — large-v2 vs large-v3 comparison resolved, large-v3 adopted:**
Two-way comparison run on `2026-06-09_audio_tho-meet.m4a` (25.2 min, 4
speakers). Findings:

- **Speaker labels:** identical between models (diarization is pyannote's job,
  not Whisper's) — expected, confirms model choice doesn't affect this.
- **Hallucination check:** no red flags. Zero segments crossed the
  low-confidence threshold (avg_logprob < -0.5) in either version.
  Consecutive-duplicate-segment counts were low and similar (6 vs 4), and all
  were short natural repeats ("Yep.", "Excellent."), not fabricated looping
  text. `large-v3`'s reputation for hallucinating in silence didn't materialize
  on this recording.
- **Confidence:** `large-v3` modestly better — avg segment logprob -0.125 vs
  -0.312 for `large-v2`; avg word confidence 0.699 vs 0.696.
- **Readability tradeoff:** `large-v3` produced ~30 fewer words overall, mostly
  by dropping short backchannel filler ("Yeah.", "Right.", "So") that `large-v2`
  kept. Cleaner to read; also quietly discards some acknowledgment cues.
- **Accuracy:** 84% word-level agreement overall. Two specific divergences
  flagged for audio spot-check but not independently verified: at 2:26,
  `large-v2` produced "and I have eight of" where `large-v3` produced "Anne will
  anger" (possible proper-noun divergence around a name); at 12:37, `large-v3`
  included a full extra sentence ("with... Come back a month later, no, I
  haven't really done anything on this.") not present in `large-v2` at all.

**Decision:** adopt `large-v3` as the default. Nothing in the hallucination
check — the original reason for caution — showed up, and confidence metrics
favor `large-v3`. The two flagged timestamps are open questions, not blockers.
Baseline comparison (Zoom's own transcription) remains deferred to a future
meeting, per the revised scope above.

**Implemented same day:** `transcribe.sh`'s hardcoded `--model` flag, and all
example commands in `README.md`, `docs/installation.md`, and
`docs/reference.md`. Two performance claims in `docs/installation.md` (10–15×
realtime on M1 Max; ~3-5x slower on Intel) were measured for `large-v2`
specifically and were not silently carried over — both now note the figure is
`large-v2`'s, not verified for `large-v3`.

While checking `docs/reference.md` for model references, found it had been
missed by two earlier passes entirely: it still shows the pre-rename script
names (`transcribe.R`/`transcribe.py`, should be `summarize-transcript.R`/
`.py`) and every path still points at `output/meeting.json` (the old in-repo
location, not the archive). Only the model flag was fixed here — the rest is
tracked as a separate cleanup task, not folded into this one.

**2026-07-11 — pyannote model mismatch resolved via source inspection, no token
test needed:** Read `whisperx/diarize.py` directly (installed package source,
not just log output): line 101 hardcodes
`model_config = model_name or "pyannote/speaker-diarization-community-1"`. Since
`transcribe.sh` never passes a model override, WhisperX always requests
`community-1` — this is unconditional, not environment-dependent.

Cross-checked `community-1`'s official HuggingFace model card: it's
self-contained, benchmarked _against_ `speaker-diarization-3.1` as a separate
"legacy" model, not built on it. Its own setup instructions require accepting
only its own license — no mention of `3.1` or `segmentation-3.0` as
dependencies.

**Resolution:** `docs/installation.md`'s HuggingFace Setup now says to accept
only `pyannote/speaker-diarization-community-1`'s license. The old instruction
(accept both `segmentation-3.0` and `speaker-diarization-3.1`) asked for
licenses this pipeline doesn't actually use.

One caveat kept honest rather than overclaimed: this rules out `3.1` and
`segmentation-3.0` as requirements with high confidence (source code + official
model card), but can't fully rule out some other undocumented gated
sub-component `community-1` might pull in — that would only surface empirically,
via an actual fresh-account test, which wasn't run.

**2026-07-11 — Tier 1 review-tooling changes built (compact flagged-words
report, speaker-slot caching):**

`--report` flag added to `review_transcript.py`: writes a plain-text file of
only words below the confidence threshold, each with timestamp, speaker, and
surrounding context (bold-marked target word) — tested against
`2026-06-09_audio_tho-meet_large-v3.json` (118 words below 0.20), confirmed
context resolves ambiguous flags like the earlier "Anne will anger" case.

Speaker-slot caching added: subject slug parsed from the filename's
`yyyy-mm-dd_subject-name` convention (override with `--subject`); speaker names
saved via `--save-speakers SPEAKER_00=Name,...` are stored in a
`.speaker-cache.json` file next to the transcript and pre-filled automatically
next time a transcript with the same subject is opened. Tested end-to-end: saved
names for subject `tho-meet`, confirmed the second run printed the cached names
and the generated HTML's embedded `KNOWN_NAMES` matched.

Both were built and tested in the sandbox against a copy of real transcript data
(not the read-only upload), no changes needed to the archive folder or existing
HTML review flow. No known issues; open question of whether the caching actually
helps in practice is left to real use, not testable synthetically.

**2026-07-12 — `~/bin/transcribe` drift item dropped, not pursued:** Parked
earlier the same day after a `diff` genuinely showed the installed copy stale
(missing the sidecar block, still on `large-v2`, still on the pre-archive
`output_dir`) — that finding was real. But the actual cause of that day's
confusing test result (a July 11 23:50 file landing in the archive despite
the stale script's `output_dir` pointing elsewhere) turned out to be simpler:
the July 11 run used `whisperx` directly, not the `transcribe` wrapper at
all. Decided not to build any of the drift-prevention options (Makefile
target, symlink, version check) — dropped rather than left parked.

**2026-07-12 — [Tier 2] Audio-linked spot-checking for flagged words,
resolved:** Listening to a flagged word resolves ambiguity a confidence
score alone can't (the "Anne will anger" case from the large-v2/v3
comparison). Built in three steps:

1. **Sidecar** (2026-07-11 design, verified 2026-07-12): `transcribe.sh`
   writes `.source-audio.json` before its `exec` call, mapping each output
   stem to its resolved source audio path — chosen over embedding the path
   in whisperx's own JSON, which would've required dropping `exec` for a
   post-process/patch step. Verified in a sandbox (spaces-in-path,
   merge-not-overwrite across runs) and against a real `transcribe` run once
   an unrelated snag was found: the installed `~/bin/transcribe` had drifted
   from the repo's `transcribe.sh` (see dropped item above).
2. **`--report` timestamp accuracy fix:** found while scoping the clip
   command that `build_flagged_report` reported each flagged word's
   *segment* start time, not the word's own — for a word late in a long
   segment, clipping around the reported timestamp would've missed the word
   entirely. Confirmed via a real transcript
   (`2026-06-09_audio_tho-meet.json`) that whisperx's alignment step does
   record per-word `start`/`end`; `load_segments` just wasn't carrying it
   through. Fixed and verified with two synthetic cases: a word 19s into a
   0-start segment now reports `[0:19]` (was `[0:00]`), and a word without
   its own alignment still falls back to the segment start rather than
   erroring.
3. **`--clip TIMESTAMP` command:** reads `.source-audio.json`, looks up the
   transcript's stem, ffmpeg-clips `±3s` (default, `--clip-padding`
   adjustable) around the timestamp into a `.wav` next to the transcript.
   Accepts `M:SS`, `H:MM:SS`, or raw seconds — same format `--report`
   prints, so a timestamp copies straight across. Verified end-to-end in a
   sandbox with a synthetic tone file: `ffprobe` confirmed the clipped
   duration matched the requested window exactly, and a missing sidecar
   entry fails with a clear message rather than a crash.

Not yet exercised on a real flagged word from a real recording — sandbox
and synthetic-data tested only, same caveat as Tier 1's speaker-slot
caching.

**2026-07-12 — [Tier 2] Cross-model disagreement as a confidence signal,
resolved (scope capped deliberately):** Cost decision: proceed — `large-v3`
measured at 26:36 wall-clock for a ~25 min recording, doubling for a second
model (~53 min) accepted as worth it, since transcription runtime wasn't
the actual friction (confidence in output, file management, and manual
step count were).

Built `compare_transcripts.py` (new standalone script, not folded into
`review_transcript.py` — comparing two transcripts is a different shape of
task than reviewing one): flattens each transcript into a chronological
word list, normalizes for comparison, runs `difflib.SequenceMatcher` to
align and report divergences with timestamps. Verified against synthetic
data, then against the real `2026-06-09_audio_tho-meet` large-v2/v3 pair —
found both previously-documented divergences exactly (`[2:26]` "Anne will
anger", `[12:37]` the extra sentence), plus 162 more, at 89.7% raw
word-level agreement. That the models substantially agree once accounted
for is itself a confidence-building result, independent of whether the
tool sees regular use.

Considered and rejected confidence-score filtering for noise reduction —
would silently hide the exact class of error (both models confident, both
wrong or different) this feature exists to catch. Built a small explicit
filler-word filter instead (`um`, `uh`, `yeah`, `yep`, `okay`, `ok`,
`right`, `so`) plus a raw/content dual agreement metric. Real impact was
modest: 164 → 124 disagreements (~24%), 89.7% → 90.5% agreement. Most of
what remained was the same category of noise just outside the 8-word list
(`gonna`/`going to`, `till`/`until`, `2 PM`/`2pm`, a name spelled three
different ways).

**Decision:** stop here rather than keep expanding the filler list.
Diminishing returns, and further noise reduction needs actual judgment
about whether a divergence is substantive — not more hand-maintained word
rules, which risk the same false-positive fragility already flagged for
the parked spell-check idea. That need is exactly Tier 3 (LLM
plausibility/sanity pass), promoted to in-progress as the direct next
step rather than parked further.

**2026-07-12 — "Spell-check pass on transcript JSON" closed, superseded:**
The original idea (a dictionary-based spell-check flag in
`review_transcript.py`, layered with a custom institution-vocabulary word
list to avoid false positives) is now redundant. `sanity_check_transcript.py`
does the more capable version of the same job — semantic implausibility
detection plus a `known-terms.txt` vocabulary list — built as Tier 3, per
the original scoping note that treated these as one combined feature, not
two separate builds. Nothing lost by closing this; the open question it
posed ("second flag type in the review tool, or a separate pass?") was
answered in practice: separate pass, `sanity_check_transcript.py`.

**2026-07-12 — R path dropped, `summarize-transcript.R` removed:** Raised
as an open question the same day (parked item, above the Tier list) — not
used for any analysis outside this pipeline, and already the *only*
R-specific file in an otherwise Python/bash toolchain (`review_transcript.py`,
`compare_transcripts.py`, `sanity_check_transcript.py`, `transcribe.sh` are
all Python/bash). Concrete cost: every recent change had to be applied
twice — today's engine-default flip, the large-v3 adoption, and the
external-archive migration all touched both `summarize-transcript.R` and
`summarize-transcript.py` separately. Decided to drop rather than keep
paying that cost for a path that wasn't being used.

Removed `summarize-transcript.R` entirely. Updated every doc reference:
`README.md` (file table, Project Structure tree — also updated to include
`compare_transcripts.py`/`sanity_check_transcript.py`/`known-terms.txt`,
which had drifted out of date independently of this change; "How It Works"
diagram and independence argument; Step 2 section — R version removed,
Python version's redundant `--engine anthropic` flags dropped now that
it's the default; checklist), `docs/reference.md` (R Pipeline Reference
section removed; Step 2 examples, custom-prompt example, and both
"In R:" backend labels converted to Python-only), `docs/installation.md`
(R packages install step removed from all four platform Quick-Start
sections, renumbering subsequent steps where needed; "Verify in R" testing
step replaced with a Python equivalént — there wasn't a separate Python
verify step to fall back to, so this was a real gap, not just a deletion;
two R-specific troubleshooting entries removed/rewritten, including giving
the `ANTHROPIC_API_KEY not set` entry an actual fix for the Python path
rather than the R-specific non-fix it had — the same `.Renviron`-isn't-
automatically-exported issue identified earlier the same session for
`transcribe.sh`'s `HF_TOKEN` handling).

Verified clean with a full-repo grep for R-specific patterns after all
edits — no remaining references.

**2026-07-12 — [Tier 2] `compare_transcripts.py` second hardening test,
`mentor-meet` large-v2/v3:** Backed up existing `mentor-meet.json` to
`mentor-meet_large-v2.json`, re-ran `transcribe` for a fresh `large-v3`
pass, diffed the pair. Raw agreement 94.8% (4378/4617 words), content
agreement 95.4% (4225/4431, filler removed), 174 disagreements shown —
higher than `tho-meet`'s 90.5%, confirming agreement rate is a
per-recording signal, not a fixed baseline.

Standout finding: "PEDON" (soils term — a 3D soil-sampling unit) at
`[8:30]`, `[8:31]`, `[18:33]`. `large-v2` mangled it as "heat on" / "PDON";
`large-v3` transcribed it correctly all three times. Jason notes he may
have mispronounced the term in the recording — if so, `large-v3` recovering
the correct word despite non-standard pronunciation is a stronger result
than a clean pronunciation would have been. Rest of the diff is mostly
`large-v3` picking up conversational filler/asides `large-v2` dropped
("you know,", "–", "Hmm", longer run-ons) — no other clear correctness win
either direction found on a skim.

**Open, not decided:** whether this settles `large-v2` vs `large-v3` as
canonical for `mentor-meet`. Not started without explicit ask.
