# Session notes — 2026-07-12

## Project

`audio-transcription-pipeline` (WhisperX + pyannote + Python summarization,
R path removed this session) for Jason Tinant, OLC. Repo:
`~/PROJECTS/audio-transcription-pipeline`. Outputs (JSON transcripts,
cleaned text, summaries) land in a separate, private, local-git-only repo:
`~/PROJECTS/audio-transcription-output` (flat, no remote, not connected to
Cowork — all interaction with it is via pasted terminal output).

Two-repo git discipline holds: git commands are never run via the sandbox
on the real repos. `WATERSHED.md` (in the pipeline repo) is the durable
record of parked decisions and resolved history — check it and the most
recent session notes before resuming.

## What changed this session

**Tier 2, both items resolved:**

1. Audio-linked spot-checking — `transcribe.sh` now writes
   `.source-audio.json` (stem → source audio path) before its `exec` call.
   `review_transcript.py` gained `--clip TIMESTAMP` (ffmpeg-clips ±3s
   around a flagged word using the sidecar). Along the way, fixed a real
   bug: `--report` was reporting a flagged word's *segment* start time
   instead of its own word-level timestamp.
2. Cross-model disagreement — new `compare_transcripts.py` diffs two
   transcripts word-by-word (`difflib`). Real test on `tho-meet`
   large-v2/v3: 89.7% raw agreement, 164 disagreements. A filler-word
   filter only improved this to 90.5% / 124 — diminishing returns, decided
   to stop rather than keep expanding the word list.

**Tier 3 built and validated with real data:** `sanity_check_transcript.py`
— LLM plausibility pass, flags semantically odd phrases against a
`known-terms.txt` vocabulary list. Tested both engines on `tho-meet`:
Ollama (7 flags, 1 unmatched, some informal-speech false positives) vs.
Anthropic (6 flags, all verbatim-matched, several independently
corroborated by `compare_transcripts.py`'s findings at the same
timestamps). **Decision: the engines are not interchangeable — Anthropic
(Claude) becomes the pipeline-wide default, Ollama stays as the
local/privacy-focused option, not a fallback.** Rolled out across
`summarize-transcript.py`, `sanity_check_transcript.py`, README,
`docs/reference.md`, `docs/installation.md` — including a real fix, not
just relabeling: README's privacy claim ("never have to leave your
computer") was rewritten, since transcript text now leaves the machine
under the new default.

Ran a second precision test on a previously untouched transcript
(`mentor-meet`, Anthropic default): 5 flags — 1 confirmed exact catch
("barbs" → "varves"), 2 likely-real, 2 false positives (unusual-but-true
colloquial phrasing). Rough 3/5 real on this sample, logged as a signal
not a stable rate.

**R path removed:** decided R wasn't adding value over the Python stack
already in daily use. Deleted `summarize-transcript.R` entirely; updated
README, `docs/reference.md`, `docs/installation.md` to remove all R
references. Caught one real gap while doing this — the install docs'
"Testing Your Setup" step only had an R version, so it was replaced with a
Python equivalent rather than just deleted.

**Housekeeping in `~/PROJECTS/audio-transcription-output`:**

- Found and removed a duplicate "[Tier 3]" section in `WATERSHED.md` (a
  stale leftover from when it was first promoted out of Parked).
- Deleted all five `_review.html` files (regeneratable from JSON).
- Resolved a redundant `tho-meet.json` vs. `tho-meet_large-v3.json` pair
  (identical content) — kept the canonical unsuffixed name plus the
  `large-v2` comparison copy.
- Backed up `mentor-meet.json` to `mentor-meet_large-v2.json` before
  re-running `transcribe` to get a fresh `large-v3` pass, for a second
  real `compare_transcripts.py` hardening test. **That transcribe run
  completed this session** but the diff itself hasn't been run yet.

## Not yet done / commit status uncertain

- **`compare_transcripts.py` has not been run on the new `mentor-meet`
  large-v2/v3 pair yet** — this is the direct next step, and the actual
  reason this session's hardening effort isn't closed out.
- A `git add WATERSHED.md; git commit -m "..."` command was given for the
  duplicate-Tier-3 fix and mentor-meet precision-test log, but not
  explicitly confirmed as run. Worth checking `git status` before
  resuming.
- Minor, unresolved: `tho-meet_large-v2.json` showed a hard-link count of
  2 in a directory listing — not investigated, probably nothing.

## Still parked / pending (in WATERSHED, not started)

- Making the installed `~/bin/transcribe` wrapper easy to keep in sync
  (Makefile target vs. symlink vs. startup version check) — raised this
  session as the next friction point (manual step count) once the
  confidence-in-output work (Tier 2/3) wrapped.
- Tier 4 — speaker inference from transcript content; speaker
  auto-labeling via voice embeddings.
- `summarize-transcript.py`'s hyphenated filename blocking clean Python
  import — now has two consumers depending on the `importlib` workaround
  (`sanity_check_transcript.py` added this session), no decision made.
- torchcodec warnings (cosmetic); diarization `std()` warning (cosmetic,
  confirmed this session to occur with or without pinned speaker count).

None of the above should be started without an explicit ask.
