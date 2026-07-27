# Session notes — 2026-07-24

## Project

`audio-transcription-pipeline`. Long session, run in Cowork. Started as a
read-only repo review and turned into two measurement runs and a new
capability. Nothing was pushed; all work is local commits or uncommitted at
time of writing.

## Shape of the session

Five threads, in order:

1. Read-only review → four change sets
2. Cowork reference docs (permission modes, model selection)
3. Model default measured, not assumed — two A/B runs
4. Speaker-name injection built (four of five approaches)
5. A latent API-response bug, found by running the thing

## 1. Read-only review

Full pass over tracked files. Findings and fixes, applied in the agreed
order:

- **`--merge` dropped the `--model` override.** `run_pipeline_merged` called
  `merge_summaries` without `model`, so the merge silently used the default
  even when both summary runs used an override.
- **`transcribe.sh` hardcoded `~/PROJECTS/audio-transcription-pipeline`**,
  but the Makefile symlinks from `$(CURDIR)` and installation.md says clone
  anywhere. Now resolves the repo from the script's own symlink-resolved
  path. Also: `HF_TOKEN` now falls back to the environment (the WSL2 docs
  told users to export it, while the script only read `~/.Renviron`), and the
  grep is anchored and capped at one match so commented-out or duplicated
  lines cannot produce a multi-line token.
- **Three broken README links**, two pointing into gitignored
  `docs/references/`. Links removed rather than publishing personal
  reference material.
- **`review_transcript.py` HTML was injectable** — transcript words, typed
  speaker names, and the search box all reached `innerHTML` unescaped, and
  the embedded JSON was not `</script>`-hardened. Tested with a hostile
  transcript before and after.

Housekeeping: a stale `.git/index.lock` from a sandbox `git status` was
removed.

## 2. Cowork reference docs

Two evergreen notes in `docs/references/` (gitignored, written for
propagation to other repos):

- `cowork-permission-modes.md` — what changes between manual and automatic
  approval. Core point: `CLAUDE.md` rules are instructions, not enforcement.
  Under manual approval the prompt is an independent backstop; under auto,
  both layers become model judgment, and the safety classifier looks for
  generic harm, not for *this repo's* rules. "Never push" is not dangerous in
  the classifier's sense.
- `cowork-model-selection.md` — model lineup, costs, and the credit-expiry
  trap. Raising the default tier is real value; manufacturing work to spend
  a balance is not.

## 3. Model default: measured, not assumed

**Change:** `claude-sonnet-4-6` (pinned in four places) → a single
`DEFAULT_ANTHROPIC_MODEL` constant, `claude-opus-5`, overridable by
`--model` or the `SUMMARIZE_MODEL` env var.

**The bigger finding was not the model.** `max_tokens` was pinned at 1024 —
roughly 750 words — which silently truncated any long summary with no error
and no signal. Model choice was never the binding constraint on a 3-hour
lecture; output length was. Raised to 8192, then to 16000 after measurement
showed Opus using 73% of 8192 on a 2h09m recording. Timeout 60s → 900s.

**Two A/B runs** via `tmp_compare_models.py` (gitignored probe), which
reports wall-clock, exact tokens and cost from the API's usage block, and
`stop_reason`:

| Run | Sonnet 5 | Opus 5 |
| --- | --- | --- |
| ESIIL, 2h09m, `lecture` | 758 words, $0.1431 | 2,299 words, $0.4523 |
| MEFA, 51m, `research` | 669 words, $0.0633 | 1,481 words, $0.2049 |

**Corrected a doc error of my own making:** cost figures written earlier the
same day were token arithmetic and wrong by ~2x. Transcript text tokenizes
at **~2.2 chars/token, not ~4** — the `[SPEAKER_00 @ 1234.5s]` prefix is
dense in digits and brackets. Real rate ~470 input tokens per minute of
audio.

**Where the decision landed:** Opus stays default, on narrower grounds than
first claimed. Only the detail-depth finding survived both runs. See
WATERSHED for the full scoring.

## 4. Speaker-name injection — the session's real result

**Turning point.** The MEFA run showed `Jason` — 11 mentions, the
most-named person in the transcript — absent from *both* models' summaries,
while Opus had plainly captured his contributions and filed them under
`SPEAKER_04`. Nothing in the pipeline ever resolved that label. The defect
was model-independent, and larger than the model-choice question two
comparison runs had been spent on. It jumped the queue.

Five approaches mapped (unsupervised → supervised), four built:

| Approach | Mechanism | Status |
| --- | --- | --- |
| 4 — cache | substitute from `.speaker-cache.json` | built |
| 3 — roster | closed-vocabulary LLM attribution | built |
| 1 — inference | unconstrained LLM attribution | built, off by default |
| 2 — VTT alignment | `map_speakers.py` | built |
| 5 — embeddings | voice matching | still parked |

Approach 4 ranks first because it is the only one that **cannot be wrong**:
a label either has a saved name or keeps `SPEAKER_XX`. Both inference
prompts require every attribution to be marked `(inferred)`, following the
existing Tier 4 finding that a confidently wrong name is worse than an
anonymous one.

**`map_speakers.py`** promotes both Zoom probes into one committed tool —
the "two more tools to maintain" cost that kept this parked was avoidable by
folding the VTT converter in as `--convert-only`. Mappings below an 80% vote
share are reported but never written.

**Validated on real data.** Three labels supplied exactly, two left to the
roster. The model returned Barry Logan and Timothy McCay — matching
independent video verification — and cited its evidence. Every "next step"
in the resulting summary now has an owner.

Tests: 53 → 98.

## 5. Latent bug, found by using it

`response.json()["content"][0]["text"]` raised `KeyError: 'text'` in real
use. `content` is a list of blocks and text is not guaranteed to be first —
with adaptive thinking, a `thinking` block can precede the answer. Because
thinking engages *adaptively*, this failed intermittently: the same request
could succeed twice and crash on the third run.

Reviewed this file twice today without catching it. It only surfaces when
the response shape actually varies, which is exactly why it sat there.

## Decisions

- `claude-opus-5` stays default, but its standing is **open, not settled** —
  only one of three supporting findings survived both runs.
- `DEFAULT_MAX_TOKENS` = 16000, sized from measurement.
- Speaker-name injection promoted ahead of the probe-promotion session it
  was originally scheduled behind.
- Participant names stay **out** of the tracked `known-terms.txt`; a
  gitignored `_scratch-files/known-terms-local.txt` holds them instead.
  Publishing colleagues' names to a public repo is effectively irreversible.
- Pre-registering predictions before a comparison run is now the practice.

## Method note: three errata, all in one direction

Three over-readings occurred across the two comparison runs, **all
favouring Opus 5**:

1. Inferred "Caitlin" was fabricated because Dr. Ramadan was confirmed real
   — treating confirmation of one name as evidence against another.
2. Reported Opus ahead on coverage from marks against a *synthetic* ranking;
   real data reversed it.
3. Scored `ARIN` as a correct catch because it looked like an acronym. The
   real form is **ERIN** and neither model found it.

Each was corrected only when Jason supplied a fact from outside the
evidence. Three errors in one direction is not noise — a conclusion was
formed early and evidence fitted to it afterwards.

Two safeguards adopted: **pre-registration**, which is the only reason a
refuted prediction got recorded rather than reinterpreted; and **reading the
coverage table for variant spellings**, since `Aaron`/`ARIN`/`Erin` as
adjacent rows was the mistranscription signal sitting in the output,
misread as three separate entities.

A fourth guess — that `LaRue` was a mangling of `Laurie` — was recorded as
*likely* rather than established, and turned out wrong. LaRue is a real
researcher. Hedging is why that is a footnote and not a fourth erratum.

## Open, carried forward

- **MEFA is transcribed as "MIFA" throughout and the summary propagates
  it.** `known-terms.txt` does not help: it is read only by
  `sanity_check_transcript.py`, never by the summarizer, which has no
  vocabulary hinting of any kind. Needs a decision.
- **`stop_reason` is not surfaced in normal use** — only the comparison
  harness reports it, so truncation remains invisible in the pipeline
  proper.
- **`.speaker-cache.json` lives next to the input**, so moving a transcript
  orphans its names. Fine today; worth knowing before reorganizing.
- Approach 5 (voice embeddings) unchanged — still gated on the cheaper
  paths proving insufficient, and four of them now exist.
- Whether model choice should be **per-preset** rather than global.
