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

- Minor, unresolved: `tho-meet_large-v2.json` showed a hard-link count of
  2 in a directory listing — not investigated, probably nothing.

## `compare_transcripts.py` run: mentor-meet large-v2/v3 (closed out)

Git confirmed up to date (duplicate-Tier-3 fix and mentor-meet
precision-test log commits went through). Ran the pending diff:

- Raw agreement: 94.8% (4378/4617 words) — content agreement 95.4%
  (4225/4431, filler removed), 174 disagreements shown. Higher than
  tho-meet's 90.5% — confirms agreement rate isn't stable across
  recordings, signal not a fixed baseline.
- Standout: "PEDON" (soils term, a 3D soil-sampling unit) at [8:30],
  [8:31], [18:33]. large-v2 mangled it as "heat on" / "PDON"; large-v3
  got it right all three times. Jason notes he may have mispronounced it
  in the recording — if so, v3 recovering the correct term despite
  non-standard pronunciation is a stronger result, not a weaker one.
- Rest of the diff is mostly v3 picking up conversational filler/asides
  v2 dropped ("you know,", "–", "Hmm", longer run-ons) — no other clear
  correctness win either direction on a skim.
- **Open, not decided:** whether this settles large-v2 vs large-v3 as
  canonical for `mentor-meet`. Not started without explicit ask.

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

---

# Session 2 — 2026-07-12 (repo-sharing readiness)

Repo connected directly via Cowork folder access this session (first
time — prior sessions worked from uploads). Ask: full-project read,
find and fix WATERSHED inconsistencies, then evaluate the repo as if
sharing it with a pyannote dev.

## Consistency pass (committed, batch 1)

- Tier 3 (sanity pass) had been left "in progress" under Parked after
  the work completed — moved to Resolved/History; Parked intro updated
  (only Tier 4 remains). Cosmetic fixes (doubled `---`, typo).
- Two WATERSHED claims contradicted the repo and were reconciled:
  `installation.md` troubleshooting still said "two model pages"
  (community-1 is the only gated model), and `summarize-transcript.py`'s
  `ANTHROPIC_API_KEY` error message still gave the `.Renviron (R)`
  non-fix. Both fixed; the R-removal entry's "verified clean" claim
  corrected with a dated note. Lesson repeated: pattern greps miss prose
  and string literals.

## Sharing evaluation → blockers (committed, batch 1)

- **Privacy: resolved by decision, not deletion.** Reviewed the
  transcript fragments and first names in WATERSHED/session notes and
  judged them innocuous; session notes stay. (Removing them wouldn't
  have helped much — WATERSHED carries the same material, and git
  history retains committed files.)
- **License chosen: PolyForm Noncommercial 1.0.0**, copyright C. Jason
  Tinant — after a plain-language comparison of MIT/Apache/GPL/CC-BY.
  Verbatim canonical text in `LICENSE.md`; README License section.
  Noted honestly: source-available, not OSI open source.
- **Stale docstring fixed:** `summarize-transcript.py` still named
  itself `transcribe.py` and suggested `from transcribe import
  run_pipeline`, which the hyphenated filename never allowed.

## Second tier (committed, batch 2)

- `requirements-lock.txt` — exact versions extracted from the venv's
  dist-info (whisperx 3.8.6, pyannote.audio 4.0.4, torch 2.8.0,
  torchcodec 0.7.0); referenced from installation.md's new "Exact
  Versions" section.
- Real bug: `transcribe.sh` interpolated paths into the sidecar
  `python3 -c` text — an apostrophe in a path (Zoom's own
  `...(he_they)'s` folder naming) would have broken it. Now argv;
  verified in sandbox with exactly such a path.
- `PYTHONWARNINGS` comment made honest (never caught the torchcodec
  warning); behavior unchanged.
- `review_transcript.py`: platform-aware opener (`open`/`xdg-open`)
  replacing macOS-only calls.
- `grant_planning` preset surfaced in `--list-types`, reference.md's
  table, and README's supported-types line (existed in prompts + README
  table only).

## Also diagnosed, no repo change

Editor showed 3× "Cannot find module httpx" — static checker pointed at
system Python 3.9, not the venv (3.11.11, httpx 0.28.1 confirmed at
runtime). Fix is interpreter selection in the editor, not code. Three
diagnostics = the three lazy `import httpx` sites.

## Next steps (decided, not started)

1. ~~Session notes entry~~ (this).
2. Small polish: real clone URLs (needs the GitHub URL), prune
   `.gitignore`'s vestigial R section, mark the "3+ speakers degrades"
   diarization claim as anecdotal.
3. The share itself: decide what is wanted *from* the pyannote dev —
   if diarization feedback, distill the `std()` warning/short-segment
   observations into a short note or issue draft rather than sending
   the bare repo link.

Deliberately not done (no decision forced): committing unit tests,
env-var override for the hardcoded archive path.

## Closed later this session

- Step 2 polish done and committed: real clone URLs
  (github.com/cjtinant/audio-transcription-pipeline), `.gitignore` R
  section pruned, diarization claims marked anecdotal (and the "audio
  energy patterns" mechanism description corrected to embedding
  clustering).
- **Step 3 closed: replied to Thomas at pyannoteAI** (engineer,
  GitHub `thomasmol`) in the May 4 email thread with the public repo
  link. Context: the original "Hervé" welcome email was automated
  onboarding; Thomas's "I'll have a look" was the real human opening,
  left unanswered since May 4. Reply included the R-fork removal, the
  version pins, and two pyannote-specific items: the short-segment
  `std()` warning, and whether the parked Tier 4 embeddings idea
  (`return_embeddings=True` speaker library) is sensible or a known
  footgun. Both of those parked items are now effectively
  awaiting-expert-reply.
