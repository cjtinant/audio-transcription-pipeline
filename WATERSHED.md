# Watershed

Next steps, open questions, and unresolved decisions. Move items to a commit or
close them when resolved.

---

## Parked:

### Review tooling ideas — priority order

Ranked by effort-vs-value when first triaged (2026-07-11). Tiers 1–3 have
since been built and resolved — see Resolved/History. Only the Tier 4
ideas below remain parked; both are speculative and carry real
misattribution risk, so neither should start without an explicit ask.

---

### Promote the Zoom-comparison probes into committed tools?

**Status:** parked — decision, not started

Two `tmp_`-prefixed, gitignored one-offs earned their keep on first use
(2026-07-14, ESIIL session — see Resolved/History): `tmp_vtt_to_json.py`
(Zoom WebVTT → WhisperX-shaped JSON, enabling `compare_transcripts.py`
and `review_transcript.py` against Zoom's output) and
`tmp_map_speakers.py` (text-alignment speaker-name transfer from a
named reference transcript, with self-flagging vote shares). Zoom VTTs
will recur (the ESIIL course alone runs for weeks), so the case for
promoting both — proper names, tests, README/reference documentation —
is real. Costs: two more tools to maintain, and the name-transfer
probe's framing overlaps the Tier 4 items below, so promoting it should
be decided together with (or instead of) those, not in addition. Worth
its own session; input from the pyannoteAI thread may also land first.

**Flagged:** 2026-07-14

---

### Speaker-identity reference signals — a taxonomy for the Tier 4 decision

**Status:** parked — design map, not a build item; feeds the same decision
as the probe-promotion item above and the two Tier 4 items below

Diarization yields anonymous clusters; naming them requires a reference
signal that carries names. Five options, cheapest-first, each covering a
case the previous one can't (raised 2026-07-14, prompted by Jason's
seeding and video-frame ideas):

1. **Named reference transcript** (Zoom cloud `.transcript.vtt`) —
   proven 2026-07-14: text-alignment name transfer at ~99.7% vote share
   with self-flagging of merged labels. Only exists for cloud
   recordings on platforms that emit named transcripts.
2. **Roster seeding** (supply expected names upfront — from calendar,
   chat log, or a `--speakers` flag). Cannot bind names to voices by
   itself (clustering never sees names), but: pins the speaker count
   exactly (would have prevented the `--max_speakers 4` miscalibration
   on the 11-voice ESIIL session), feeds `--hotwords` so spoken names
   transcribe correctly, and gives the LLM-inference idea below a
   closed vocabulary — a large cut to its misattribution risk.
3. **Roll-call protocol** (meetings Jason controls): a brief go-around
   at the start binds names to clusters directly via self-introduction.
   Zero engineering; useless for meetings he merely attends.
4. **Video-frame OCR of name tags** (Zoom `.mp4` active-speaker view):
   name-at-time-t aligned to diarization segments. Only earns its
   complexity where no named VTT exists (Zoom *local* recordings, other
   platforms, handed-over videos) — the pixels carry the same account
   metadata the VTT gets for free. Heaviest option short of embeddings.
5. **Voice embeddings** (Tier 4 item below): the general solution that
   needs no per-recording reference — enrollment cost, cold-start, and
   confidently-wrong risk as already flagged; input awaited from the
   pyannoteAI thread.

**New evidence for the LLM-inference item (2026-07-14):** the ESIIL
lecture summary spontaneously attributed live-demo participants by
name, correctly (verified against Zoom's roster) — the LLM inferred
identity from vocatives in the content, unprompted, despite the merged
diarization labels. The name-address pattern is clearly common in
instructional/live-demo sessions; whether it holds for OLC meeting
types is still the open question the queued scoping probe exists to
answer.

**Flagged:** 2026-07-14

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
reliably, producing a "std(): degrees of freedom is <= 0" warning. Transcript is
produced normally. May result in uncertain speaker labels on very short segments
(silence, crosstalk).

**Correction (2026-07-12):** originally attributed specifically to pinning
`--min_speakers`/`--max_speakers` to 2. A 2026-07-12 test run (plain
`transcribe`, no speaker-count flags set) produced the same warning — the cause
is broader than pinned speaker count, likely just short/ambiguous segments
generally. Title and description corrected; still cosmetic, still not worth
fixing until it causes an actual problem.

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
confusing test result (a July 11 23:50 file landing in the archive despite the
stale script's `output_dir` pointing elsewhere) turned out to be simpler: the
July 11 run used `whisperx` directly, not the `transcribe` wrapper at all.
Decided not to build any of the drift-prevention options (Makefile target,
symlink, version check) — dropped rather than left parked.

**2026-07-12 — [Tier 2] Audio-linked spot-checking for flagged words,
resolved:** Listening to a flagged word resolves ambiguity a confidence score
alone can't (the "Anne will anger" case from the large-v2/v3 comparison). Built
in three steps:

1. **Sidecar** (2026-07-11 design, verified 2026-07-12): `transcribe.sh` writes
   `.source-audio.json` before its `exec` call, mapping each output stem to its
   resolved source audio path — chosen over embedding the path in whisperx's own
   JSON, which would've required dropping `exec` for a post-process/patch step.
   Verified in a sandbox (spaces-in-path, merge-not-overwrite across runs) and
   against a real `transcribe` run once an unrelated snag was found: the
   installed `~/bin/transcribe` had drifted from the repo's `transcribe.sh` (see
   dropped item above).
2. **`--report` timestamp accuracy fix:** found while scoping the clip command
   that `build_flagged_report` reported each flagged word's _segment_ start
   time, not the word's own — for a word late in a long segment, clipping around
   the reported timestamp would've missed the word entirely. Confirmed via a
   real transcript (`2026-06-09_audio_tho-meet.json`) that whisperx's alignment
   step does record per-word `start`/`end`; `load_segments` just wasn't carrying
   it through. Fixed and verified with two synthetic cases: a word 19s into a
   0-start segment now reports `[0:19]` (was `[0:00]`), and a word without its
   own alignment still falls back to the segment start rather than erroring.
3. **`--clip TIMESTAMP` command:** reads `.source-audio.json`, looks up the
   transcript's stem, ffmpeg-clips `±3s` (default, `--clip-padding` adjustable)
   around the timestamp into a `.wav` next to the transcript. Accepts `M:SS`,
   `H:MM:SS`, or raw seconds — same format `--report` prints, so a timestamp
   copies straight across. Verified end-to-end in a sandbox with a synthetic
   tone file: `ffprobe` confirmed the clipped duration matched the requested
   window exactly, and a missing sidecar entry fails with a clear message rather
   than a crash.

Not yet exercised on a real flagged word from a real recording — sandbox and
synthetic-data tested only, same caveat as Tier 1's speaker-slot caching.

**2026-07-12 — [Tier 2] Cross-model disagreement as a confidence signal,
resolved (scope capped deliberately):** Cost decision: proceed — `large-v3`
measured at 26:36 wall-clock for a ~25 min recording, doubling for a second
model (~53 min) accepted as worth it, since transcription runtime wasn't the
actual friction (confidence in output, file management, and manual step count
were).

Built `compare_transcripts.py` (new standalone script, not folded into
`review_transcript.py` — comparing two transcripts is a different shape of task
than reviewing one): flattens each transcript into a chronological word list,
normalizes for comparison, runs `difflib.SequenceMatcher` to align and report
divergences with timestamps. Verified against synthetic data, then against the
real `2026-06-09_audio_tho-meet` large-v2/v3 pair — found both
previously-documented divergences exactly (`[2:26]` "Anne will anger", `[12:37]`
the extra sentence), plus 162 more, at 89.7% raw word-level agreement. That the
models substantially agree once accounted for is itself a confidence-building
result, independent of whether the tool sees regular use.

Considered and rejected confidence-score filtering for noise reduction — would
silently hide the exact class of error (both models confident, both wrong or
different) this feature exists to catch. Built a small explicit filler-word
filter instead (`um`, `uh`, `yeah`, `yep`, `okay`, `ok`, `right`, `so`) plus a
raw/content dual agreement metric. Real impact was modest: 164 → 124
disagreements (~24%), 89.7% → 90.5% agreement. Most of what remained was the
same category of noise just outside the 8-word list (`gonna`/`going to`,
`till`/`until`, `2 PM`/`2pm`, a name spelled three different ways).

**Decision:** stop here rather than keep expanding the filler list. Diminishing
returns, and further noise reduction needs actual judgment about whether a
divergence is substantive — not more hand-maintained word rules, which risk the
same false-positive fragility already flagged for the parked spell-check idea.
That need is exactly Tier 3 (LLM plausibility/sanity pass), promoted to
in-progress as the direct next step rather than parked further.

**2026-07-12 — "Spell-check pass on transcript JSON" closed, superseded:** The
original idea (a dictionary-based spell-check flag in `review_transcript.py`,
layered with a custom institution-vocabulary word list to avoid false positives)
is now redundant. `sanity_check_transcript.py` does the more capable version of
the same job — semantic implausibility detection plus a `known-terms.txt`
vocabulary list — built as Tier 3, per the original scoping note that treated
these as one combined feature, not two separate builds. Nothing lost by closing
this; the open question it posed ("second flag type in the review tool, or a
separate pass?") was answered in practice: separate pass,
`sanity_check_transcript.py`.

**2026-07-12 — [Tier 3] LLM plausibility/sanity pass built, validated, and
adopted (`sanity_check_transcript.py`):** Flagged 2026-07-11, picked up
2026-07-12 as the direct next step after Tier 2's noise-reduction ceiling,
resolved the same day. (Moved here from Parked in a 2026-07-12 consistency
pass — the item had stayed under "in progress" after the work completed.)

Original idea: feed the plain-text transcript through the summarizer's existing
LLM, asking it to flag anything that reads as semantically odd or out of place.
Catches a different error category than acoustic confidence. Scoping this out
reinforced that it shares the same false-positive risk as the spell-check idea
(institution-specific terms and proper nouns getting flagged as "wrong" by
something that doesn't know your vocabulary) — treated as one combined "sanity
pass" feature, not two separate builds.

**Why then:** `compare_transcripts.py` (Tier 2) hit a real ceiling — a
hand-maintained filler-word list only cut disagreements 164 → 124 before running
into the same false-positive risk this item already flagged. Getting further
requires actual judgment about "is this divergence/word substantive," not more
word-list rules — which is exactly what this item is.

**Skeleton built (2026-07-12):** `sanity_check_transcript.py` reuses
`summarize-transcript.py`'s `summarize_anthropic`/`summarize_ollama` for the LLM
call itself (loaded via `importlib` — the hyphenated filename issue under Parked
applies here too, worked around rather than fixed as part of this task) and
`review_transcript.py`'s `load_segments` for parsing. A prompt asks the model to
flag phrases that read as semantically odd, supplying a `known-terms.txt` list
(seeded with TEA-Center, WhisperX, pyannote, OLC/Oglala Lakota College, Lakota —
almost certainly incomplete) so legitimate vocabulary isn't flagged as error,
per the false-positive risk already identified. Output format is a simple
`FLAG:`/`REASON:` block per flag (chosen over JSON — more forgiving to parse if
a smaller local model doesn't format strictly), matched back to a timestamp by
locating the phrase in the transcript's word list.

Unit-tested what can be tested without a real model: known-terms file parsing
(comments/blanks filtered), flag-block parsing (multiple flags, `NONE FOUND`, a
phrase that doesn't match verbatim — reported as `?:??` rather than silently
dropped or crashing), and confirmed the `importlib` reuse of
`summarize-transcript.py`'s functions actually resolves.

**Real test run (2026-07-12), both engines, against
`2026-06-09_audio_tho-meet_large-v3.json`:** meaningful quality gap between
engines, not just a style difference.

`ollama` (`llama3.1:8b-instruct-q6_k`): 7 flags, 1 couldn't be matched back to a
timestamp (the model paraphrased instead of quoting verbatim, despite the
prompt's explicit instruction — a real prompt-compliance gap for the smaller
model). Several flags look like informal-speech false positives despite being
told not to flag those ("Not fine.", "And actually what we'll do is about
this."). One genuinely good catch not found by the other engine or by
`compare_transcripts.py`: `[24:21]` flagged garbled grammar ("I haven't done a
darn thing since like, I think it's all it is") and suggested a plausible real
reading.

`anthropic` (`claude-sonnet-4-6`): 6 flags, all matched verbatim — no
format-compliance issue. More striking: most of Claude's flags land on
timestamps `compare_transcripts.py` had already found suspicious, from a
completely different signal (semantic plausibility vs. cross-model
disagreement):

- `[20:58]` "lacrosse" ↔ Tier 2's `[20:59] replace: 'no cost' → 'lacrosse'` —
  exact match.
- `[19:29]` "green" ↔ Tier 2's `[19:30] insert: 'green'` — exact match.
- `[9:14]`/`[9:17]` "Wall Street"/"Causes" ↔ Tier 2's
  `[9:15] replace: "OLC... Because it's" → "the Wall Street... Causes"` — same
  region.
- `[7:24]` "Tho" ↔ Tier 2's `[7:24] replace: 'though' → 'Tho'` — same
  divergence, different theory (Claude guessed a mistranscribed proper name;
  could equally be the reverse — `2026-06-09_audio_tho-meet`'s own filename
  already uses "tho" as a subject slug, so `large-v3`'s "Tho" might be the
  _correct_ one and `large-v2`'s "though" the error. Neither tool says which
  side is right, same as `compare_transcripts.py`'s own design — human judgment
  still required.)
- `[11:04]` "Nike" is _near_ Tier 2's
  `[11:04] replace: 'Gabe at' → 'the agent of'` but "Nike" itself doesn't appear
  in that diff — meaning it's possibly a word both models transcribed
  _identically wrong_, which cross-model diffing structurally cannot see.
  Genuinely interesting if true, but unconfirmed — would need the raw JSON words
  checked directly, not done here.

**Decision (2026-07-12):** the two engines are not actually interchangeable —
this test is evidence they never were, the pipeline's docs just treated them
that way. `anthropic` (Claude) becomes the default engine pipeline-wide, not
just for this tool. `ollama` stays fully supported, reframed as the explicit
local/privacy-focused option rather than the default — a real choice for
sensitive recordings, not a downgrade path.

**Rollout completed (2026-07-12):** default engine flipped consistently across
code and docs. Code: `summarize-transcript.py`'s `run_pipeline`/
`run_pipeline_merged`/CLI default, `summarize-transcript.R`'s `match.arg()`
vectors reordered (R uses the first listed value as the default — confirmed by R
semantics, not executed; the suggested real check became moot later the same
day when the R path was removed entirely — see the entry below),
`sanity_check_transcript.py`'s CLI default. Docs: `README.md`,
`docs/reference.md`, `docs/installation.md` — every example and section label
reordered to present Anthropic first/as default, Ollama reframed as the
local/private option, not a fallback.

One thing caught and fixed along the way, not just relabeled: README's privacy
framing ("your audio and transcripts never have to leave your computer") was
accurate when Ollama was default but became a real inaccuracy once Anthropic is
default — transcript _text_ now leaves the machine unless a user explicitly opts
into `--engine ollama`. Rewrote to distinguish audio (always local) from
transcript text (sent externally only under the default engine) rather than just
swapping which option is labeled "(default)".

**First precision test on unseen content (2026-07-12):** ran
`sanity_check_transcript.py` (Anthropic, default) against
`2026-06-09_audio_mentor-meet.json` — untouched by any tool built this session,
unlike `tho-meet` which had been picked apart repeatedly. 5 flags, scored
against the user's own knowledge of what was actually said:

- **1 confirmed exact catch:** `[14:36]` "barbs" → correct answer "varves"
  (tree-ring/climate-proxy discussion). Claude didn't just find a real error, it
  supplied the right fix.
- **2 likely real catches, context confirmed but exact wording not verified:**
  `[5:53]` "cow patient" (confirmed as garbled mesonet-station discussion) and
  `[14:00]` "save your million" (confirmed as the Dakota blizzard discussion).
- **2 false positives:** `[1:50]` "plumber" and `[33:35]` "straight and to the
  right" were both actually said — Claude flagged genuine, correct colloquial
  phrasing about a person's character as semantically odd. Different failure
  mode than Ollama's informal-speech false positives from the earlier test
  (filler/backchannel) — this is unusual-but-real descriptive language, not
  filler.

**Rough precision: 3/5 real, 2/5 false positive** on a single unseen recording —
not a large enough sample to treat as a stable rate, but the first real signal
beyond the `tho-meet` test (which validated corroboration with
`compare_transcripts.py`, not raw precision). Consistent with "flags are a
signal, not a fix" — about 2 in 5 flags being dead ends here is a real cost of
using this tool, not a defect to chase down immediately. Ongoing upkeep, not a
task: add terms to `known-terms.txt` as false positives surface.

**2026-07-12 — R path dropped, `summarize-transcript.R` removed:** Raised as an
open question the same day (parked item, above the Tier list) — not used for any
analysis outside this pipeline, and already the _only_ R-specific file in an
otherwise Python/bash toolchain (`review_transcript.py`,
`compare_transcripts.py`, `sanity_check_transcript.py`, `transcribe.sh` are all
Python/bash). Concrete cost: every recent change had to be applied twice —
today's engine-default flip, the large-v3 adoption, and the external-archive
migration all touched both `summarize-transcript.R` and
`summarize-transcript.py` separately. Decided to drop rather than keep paying
that cost for a path that wasn't being used.

Removed `summarize-transcript.R` entirely. Updated every doc reference:
`README.md` (file table, Project Structure tree — also updated to include
`compare_transcripts.py`/`sanity_check_transcript.py`/`known-terms.txt`, which
had drifted out of date independently of this change; "How It Works" diagram and
independence argument; Step 2 section — R version removed, Python version's
redundant `--engine anthropic` flags dropped now that it's the default;
checklist), `docs/reference.md` (R Pipeline Reference section removed; Step 2
examples, custom-prompt example, and both "In R:" backend labels converted to
Python-only), `docs/installation.md` (R packages install step removed from all
four platform Quick-Start sections, renumbering subsequent steps where needed;
"Verify in R" testing step replaced with a Python equivalent — there wasn't a
separate Python verify step to fall back to, so this was a real gap, not just a
deletion; two R-specific troubleshooting entries removed/rewritten, including
giving the `ANTHROPIC_API_KEY not set` entry an actual fix for the Python path
rather than the R-specific non-fix it had — the same `.Renviron`-isn't-
automatically-exported issue identified earlier the same session for
`transcribe.sh`'s `HF_TOKEN` handling).

Verified clean with a full-repo grep for R-specific patterns after all edits —
no remaining references.

**Correction (2026-07-12, consistency pass):** that grep had blind spots. Two
further misses were found and fixed the same day: the `"macOS/Linux (R
users):"` prose label in `installation.md` (caught during the Makefile rollout,
noted below) and `summarize-transcript.py`'s `ANTHROPIC_API_KEY` error message,
which still told users to "Add it to ~/.Renviron (R)" — the same non-fix the
docs pass had removed from `installation.md`'s troubleshooting. The error
message now gives the shell-export fix, matching the docs. Lesson consistent
with the Makefile entry's finding: pattern greps catch code/file references,
not prose and string literals.

**2026-07-12 — [Tier 2] `compare_transcripts.py` second hardening test,
`mentor-meet` large-v2/v3:** Backed up existing `mentor-meet.json` to
`mentor-meet_large-v2.json`, re-ran `transcribe` for a fresh `large-v3` pass,
diffed the pair. Raw agreement 94.8% (4378/4617 words), content agreement 95.4%
(4225/4431, filler removed), 174 disagreements shown — higher than `tho-meet`'s
90.5%, confirming agreement rate is a per-recording signal, not a fixed
baseline.

Standout finding: "PEDON" (soils term — a 3D soil-sampling unit) at `[8:30]`,
`[8:31]`, `[18:33]`. `large-v2` mangled it as "heat on" / "PDON"; `large-v3`
transcribed it correctly all three times. Jason notes he may have mispronounced
the term in the recording — if so, `large-v3` recovering the correct word
despite non-standard pronunciation is a stronger result than a clean
pronunciation would have been. Rest of the diff is mostly `large-v3` picking up
conversational filler/asides `large-v2` dropped ("you know,", "–", "Hmm", longer
run-ons) — no other clear correctness win either direction found on a skim.

**Open, not decided:** whether this settles `large-v2` vs `large-v3` as
canonical for `mentor-meet`. Not started without explicit ask.

**2026-07-12 — `transcribe` wrapper sync fixed (symlink + Makefile), rolled
out across all platform docs:** Resolved the "keep `~/bin/transcribe` in
sync" item scoped earlier the same day. Both open design questions decided:
Positron does *not* need to become the documented default (Jason confirmed
platform-general docs are fine as written); the symlink + Makefile approach
*is* feasible for the Windows-Simple audience (WSL2 is a real Linux
userland — `ln -s`/`make` behave identically to native Linux there) and was
extended to it.

Built `Makefile` (new, repo root) with a single `.PHONY: install` target:
`ln -sf` the repo's `transcribe.sh` into `~/bin/transcribe` (idempotent,
safe to re-run) plus `chmod +x`. Replaces the old `cp`/`chmod` sequence
everywhere it appeared, and fills three places that never had an install
step documented at all:

- `installation.md` — macOS Apple Silicon (Simple + Technical) switched from
  `cp` to `make install`. Linux (Simple), Linux (Technical), and Windows
  WSL2 (Technical) each gained a net-new "Install the transcribe script"
  step (previously missing entirely) using the same command. Windows
  (Simple) already got this fix in the prior turn.
- `transcribe.sh`'s own header comment updated to match.
- `README.md`'s Project Structure tree gained a `Makefile` entry.
- Linux (Simple) and Windows (Simple) both gained `build-essential` in
  their `apt install` lines (`make`'s actual dependency, previously present
  only in the Technical tracks). RHEL/Fedora's `dnf` line also gained an
  explicit `make` package — not verified whether `gcc` alone would have
  pulled it in as a dependency, added explicitly rather than assumed.

Also fixed while doing this full-repo doc pass: the stale `"macOS/Linux (R
users):"` label at `installation.md` (flagged, not fixed, in the prior
turn) — changed to `"macOS/Linux:"`. Confirms the earlier full-repo grep
for R-specific patterns had a real blind spot (prose labels vs. literal `R`
code/file references), now closed.

`noise-reduction.md` and `cowork-folder-access.md` were read as part of
this pass and need no changes — neither references the engine default, R,
or the install method.

**2026-07-12 — Repo-sharing readiness pass (pre-share with a pyannote
dev):** Full-project read surfaced inconsistencies and gaps ahead of
sharing the repo externally. Done in two tiers the same day:

_Blockers:_ `LICENSE.md` added (PolyForm Noncommercial 1.0.0, verbatim
canonical text, Required Notice: Copyright (c) 2026 C. Jason Tinant) plus
a plain-language License section in README — noted honestly:
source-available, not OSI open source. `summarize-transcript.py`'s
docstring and `--help` epilog corrected from the pre-rename
`transcribe.py` naming; the `from transcribe import run_pipeline` example
(which the hyphenated filename never allowed) now points at
`docs/reference.md`'s importlib recipe. Privacy question resolved by
decision, not deletion: Jason reviewed the transcript fragments and first
names in WATERSHED/session notes and judged them innocuous; session notes
stay in the repo. (Removing them wouldn't have helped much anyway —
WATERSHED carries the same material, and git history retains committed
files.)

_Second tier (things a reviewer would notice):_

- `requirements-lock.txt` added — exact versions extracted from the
  venv's dist-info metadata (equivalent to `uv pip freeze`, which
  couldn't run from the session sandbox against the macOS venv):
  whisperx 3.8.6, pyannote.audio 4.0.4, torch 2.8.0, faster-whisper
  1.2.1, torchcodec 0.7.0, et al. Pins the versions behind this repo's
  version-specific claims (torchcodec warnings, `community-1` default).
  Referenced from a new "Exact Versions" section in `installation.md`
  and README's structure tree.
- Real bug fixed in `transcribe.sh`: `$audio_stem`/`$audio_path` were
  interpolated directly into the sidecar `python3 -c` program text — a
  path containing an apostrophe (Zoom's own `...(he_they)'s Zoom
  Meeting` folder naming) would have broken it. Now passed as argv with
  a single-quoted program. Verified in the sandbox with exactly such a
  path; the old form would have raised a SyntaxError.
- `transcribe.sh`'s PYTHONWARNINGS comment corrected: it claimed to
  suppress the torchcodec warning, which it never did (already
  documented in the torchcodec parked item). Comment now states what the
  line actually does (pyannote UserWarnings) and what it doesn't.
  Behavior unchanged.
- `review_transcript.py`: macOS-only `open` calls replaced with a
  platform-aware `open_with_default_app` (`open` on darwin, `xdg-open`
  elsewhere) — docs claim Linux/WSL2 support, so this was a real gap.
- `grant_planning` preset gaps closed: it existed in `MEETING_PROMPTS`
  and README's table but was missing from `MEETING_TYPE_DESCRIPTIONS`
  (so `--list-types` silently omitted it), `docs/reference.md`'s presets
  table, and README's supported-types line. All three fixed;
  `--list-types` column width bumped to fit the longer name. Verified by
  running `--list-types`.

Deliberately not done (noted in the evaluation, no decision forced):
committing unit tests (the sandbox tests from prior sessions were never
kept), env-var overrides for the hardcoded `~/PROJECTS` archive path,
replacing the `your-username` placeholder clone URLs, pruning
`.gitignore`'s vestigial R section, and softening the "auto-detection
degrades with 3+ speakers" diarization claim to explicitly anecdotal.
(The last three were done later the same day as follow-up polish; the
env-var archive path followed the same day — see entry below. Only the
unit tests remain undone.)

**2026-07-12 — Hyphenated filename resolved: `summarize-transcript.py`
renamed to `summarize_transcript.py`:** Parked 2026-07-11 with two
options (rename vs. treat CLI as the only supported pattern); resolved
in favor of the rename once three things tipped the balance the same
day: two consumers depended on the `importlib` workaround
(`sanity_check_transcript.py` plus the documented interactive recipe),
the repo had just gone public with zero external users — the cheapest
the rename would ever be — and a pyannoteAI engineer was about to read
the code, where a file-path `importlib` load of a sibling module reads
as a wart.

Mechanical rollout: `mv` (git detects the rename on `git add -A`);
`sanity_check_transcript.py`'s 8-line `importlib` block collapsed to
`from summarize_transcript import summarize_anthropic,
summarize_ollama` (its docstring note about the workaround removed);
`docs/reference.md`'s "Interactive / script usage" `importlib` recipe
replaced with a normal import (run from the repo folder or add to
`sys.path`); the renamed file's own docstring now shows the working
import; every CLI example across `README.md`, `docs/reference.md`,
`docs/installation.md` updated. Historical references in WATERSHED and
session notes left as-is — they describe the past accurately.

Verified: both files `py_compile` clean, `import sanity_check_transcript`
resolves the new import chain end-to-end, `--list-types` runs, and a
repo-wide grep confirms no live references to the hyphenated name
outside history documents.

**2026-07-12 — Archive path made overridable via `TRANSCRIBE_OUTPUT_DIR`:**
Closed the "hardcoded `~/PROJECTS` archive path" item from the readiness
evaluation's deliberately-not-done list — prioritized ahead of Tier 4
work because anyone cloning the now-shared repo hits the hardcoded path
first. Precedence: explicit `--output_dir`/`--output-dir`/`output_dir`
argument > `TRANSCRIBE_OUTPUT_DIR` env var > the unchanged default.

Implementation: `transcribe.sh` resolves `$output_dir` once (with
`mkdir -p` for robustness) and uses it for both whisperx's
`--output_dir` and the sidecar write — the sidecar previously hardcoded
the archive path inside its Python snippet, and now receives the dir as
a third argv. One documented nuance: a `--output_dir` passed on the
`transcribe` command line overrides whisperx's output but not the
sidecar location, which always follows the env/default archive.
`summarize_transcript.py` gets a module-level `DEFAULT_OUTPUT_DIR`
(reads the env var at import) used by `save_outputs`, `run_pipeline`,
`run_pipeline_merged`, and the CLI default. `review_transcript.py`
needed no change — all its outputs and sidecar reads are input-relative
by design, so it follows the archive wherever it lives. Docs: custom-
location subsection in `installation.md`'s archive setup; one-line
note in README's "Where output goes."

Verified: `bash -n` + `py_compile` clean; env override observed in both
the module default and `--help` text; sidecar written to a custom
`TRANSCRIBE_OUTPUT_DIR` with an apostrophe-containing audio path (the
quoting fix from earlier today still holds through the new argv).

**2026-07-12 — Unit tests committed (`tests/`, 48 tests):** Closes the
last deliberately-not-done item from the readiness evaluation. Prior
sessions' tests lived only in throwaway sandboxes; WATERSHED described
testing that a reader of the repo couldn't find. Now committed as four
stdlib-`unittest` files (no pytest — zero new dependencies, matching
the tools' own stdlib-only design), covering the pure functions of all
four Python tools; no LLM call or audio needed. Run with
`python3 -m unittest discover tests` from the repo root (documented in
`docs/reference.md`; `tests/` added to README's structure tree).

Regression cases encode this repo's actual bug history, not generic
coverage: the `--report` word-level-timestamp fix (a word 19s into a
0-start segment must report `[0:19]`), the unaligned-punctuation
fallback, `?:??` for unlocatable sanity flags, filler-only differences
excluded from `compare_transcripts.py`'s shown disagreements, the
`grant_planning` `--list-types` omission (as a prompts-vs-descriptions
consistency check), the `save_outputs` skip-transcript-for-`.txt`
behavior, and the `TRANSCRIBE_OUTPUT_DIR` override (tested in a fresh
interpreter, since the default is read at import). All 48 passed on
first run in the sandbox.

**2026-07-14 — Zoom-baseline comparison run (deferred since 2026-07-11),
plus a text-alignment speaker-name-transfer probe:** Real subject: the
ESIIL Data Short Course session recording (2026-07-13, 2h09m, 11
speakers per Zoom's roster), transcribed with `large-v3`,
`--min_speakers 1 --max_speakers 4`, and `--hotwords` including ESIIL
and CIRES. Zoom's own artifacts (`.transcript.vtt` with account-name
speaker attribution, `.cc.vtt` without) converted to WhisperX-shaped
JSON via `tmp_vtt_to_json.py` (a `tmp_`-prefixed, gitignored one-off;
Zoom-side word timestamps are interpolated from cue timing, so
approximate by design), then diffed with the existing
`compare_transcripts.py`.

**Text results:** 93.2% raw / 93.5% content agreement, 725 divergences.
The "pipeline is a little better on tricky science words" claim (made in
writing to UC Boulder colleagues the same day) is supported but narrow:
pipeline won `CIRES` (Zoom: "CERES"), `Corps` (Zoom: "Board,"), and
came closer on a participant's surname — but _both_ systems
mangled the spoken word "ESIIL" (Zoom: "easel"/"ESO"; pipeline:
"ESL"/"ESOL"), despite ESIIL being in `--hotwords`. Hotwords hint, they
don't guarantee. `known-terms.txt` gained ESIIL, CIRES, Earth Lab so
the sanity pass can flag these next time.

**Speaker results — the more interesting half.** The `--max_speakers 4`
pin (suggested per README's lecture guidance, miscalibrated for an
11-voice session) forced ~9 participants into 2 labels.
`tmp_map_speakers.py` (second gitignored one-off) aligned the two
transcripts word-by-word and majority-voted Zoom's account names onto
the pipeline's `SPEAKER_XX` labels: SPEAKER_00 and SPEAKER_02 both
mapped to the lecturer at ~99.7% (diarization split one voice into two
labels — harmless, votes unambiguous), while SPEAKER_01/SPEAKER_03
had no majority (42%/29% top shares) — exactly the merged buckets, and
the vote share self-flags them. Direct evidence for the Tier 4
discussion: text-alignment name transfer works where diarization is
right and announces where it isn't, at zero voice-embedding cost —
though it only exists when a named reference transcript (here, Zoom's)
exists at all. Also noted plainly: for multi-participant Zoom sessions,
Zoom's speaker attribution is structurally better (exact names, free,
from per-account audio streams); this pipeline's edge is vocabulary,
word-level confidence, and the JSON structure downstream tools need.

Process note: Jason established `99_archive/` (gitignored) inside the
repo as the place for non-sensitive test materials like this session —
distinct from the private output archive, which remains for real
recordings.

**2026-07-14 — Rate-limit retry added to the Anthropic path:** The
ESIIL summary run crashed with a 429: `--merge` fires two ~30k-token
requests back-to-back, and the second exceeded a per-minute token
window — a failure mode that never surfaced on ~25-minute meeting
transcripts and only appeared at 2h09m scale. Run 1's completed summary
was also lost in the crash (the merged pipeline only saves at the end)
— the retry prevents the crash rather than adding partial-save
plumbing. New `_post_with_retry` in `summarize_transcript.py`, used by
both Anthropic call sites (`summarize_anthropic`, `merge_summaries`):
retries 429/5xx up to 3 times, honors `Retry-After` (capped 120s),
defaults to 60s for 429 (one TPM window), fails fast on client errors
like 401. Ollama call sites deliberately unchanged (local server, no
rate limits, connection errors already handled). Five unit tests added
via injection points — 53 total, all green.
