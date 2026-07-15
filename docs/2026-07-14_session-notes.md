# Session notes — 2026-07-14

## Project

`audio-transcription-pipeline` — now public at
github.com/cjtinant/audio-transcription-pipeline, shared with pyannoteAI
(Thomas, 2026-07-12) and with UC Boulder / ESIIL colleagues by email
today. Same two-repo discipline as always; a third location,
`99_archive/` (in-repo, gitignored), was established this session for
non-sensitive test materials.

## Since the 2026-07-12 notes (pre-audible work)

- **Hyphenated filename resolved:** `summarize-transcript.py` renamed to
  `summarize_transcript.py`; importlib workarounds collapsed to normal
  imports; all docs updated. Last non-blocked Parked item at the time.
- **`TRANSCRIBE_OUTPUT_DIR`** env-var override for the archive path
  (transcribe.sh + summarizer; precedence: flag > env > default).
- **Unit tests committed:** `tests/`, 48 stdlib-unittest tests encoding
  actual bug history; `python3 -m unittest discover tests`.
- **Tier 4 #1 scoping probe** (`tmp_scoping_name_mentions.py`) built and
  parser-tested; run against real transcripts still queued.
- `tmp_*` added to `.gitignore` — scratch scripts stay local.
- Editor issue diagnosed twice over: Positron was pointed at the system
  Python 3.9 (x64 under Rosetta) — phantom httpx errors, then an
  architecture warning. Correct pick: the `uv: audio-transcription-
  pipeline` 3.11.11 entry. The interpreter sprawl (OS, Homebrew, uv,
  conda/R, old venvs) is accumulation, not breakage.

## The audible: ESIIL short-course session as a real-world test

Ran the 2026-07-13 course recording (2h09m, 11 speakers) through the
pipeline. The torchcodec `LC_RPATH` warning appeared exactly as
documented in WATERSHED — cosmetic, pyannote's fallback loader carried
on. Zoom's own artifacts (speaker-attributed `.transcript.vtt`, plain
`.cc.vtt`, chat log) made the long-deferred Zoom-baseline comparison
possible:

- `tmp_vtt_to_json.py` (one-off, gitignored): Zoom VTT → WhisperX-shaped
  JSON; then the existing `compare_transcripts.py` did the rest.
- **93.2% raw / 93.5% content agreement, 725 divergences.** The "better
  on tricky science words" claim (made in the colleague email the same
  morning): supported but narrow — pipeline won CIRES and "Corps," but
  both systems mangled the spoken acronym "ESIIL" despite it being a
  hotword.
- `tmp_map_speakers.py` (one-off, gitignored): majority-vote name
  transfer from Zoom's account names onto SPEAKER_XX labels. Lecturer
  labels mapped at ~99.7% vote share; the two labels my
  `--max_speakers 4` pin forced ~9 participants into self-flagged as
  merged (no majority). Real evidence for the Tier 4 discussion, ahead
  of any pyannoteAI reply.
- `known-terms.txt` += ESIIL, CIRES, Earth Lab.
- Full findings in WATERSHED (2026-07-14 entry); a public-safe GitHub
  issue summarizing the comparison was drafted.

## Decisions

- `--max_speakers` pinning guidance was miscalibrated for a large
  multi-participant session — README's lecture range (1–4) assumes few
  question-askers. Not yet changed in docs; noted here and in WATERSHED.
- Promote-or-park for the two probes: **parked** in WATERSHED as an
  explicit decision item, to be taken together with the Tier 4 items
  (the name-transfer probe overlaps them).

## Pending (Jason's terminal — need API key / private archive)

```bash
cd ~/PROJECTS/audio-transcription-pipeline
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-13_esiil-short-course_audio.json \
  --type lecture --merge
```

```bash
python3 review_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-13_esiil-short-course_audio.json \
  --save-speakers "SPEAKER_00=Nate Quarderer,SPEAKER_02=Nate Quarderer,SPEAKER_01=Participants (mixed),SPEAKER_03=Participants (mixed)"
```

Also still queued: Tier 4 #1 scoping run (probe ready, two commands in
the 07-12 notes era); Thomas's reply.

## Later the same day — summary run, retry fix, results

**429 crash and fix:** the first `--merge` run on the ESIIL transcript
died with a 429 on Run 2 — two ~30k-token requests back-to-back exceed
a per-minute token window, a failure mode invisible at ~25-minute
meeting scale. Added `_post_with_retry` to `summarize_transcript.py`
(honors Retry-After capped at 120s, waits one TPM window for 429, fails
fast on 401-class errors; Ollama paths deliberately unchanged; 5 new
unit tests, 53 total). Committed, then validated in production within
the hour: the rerun absorbed four 429s (including API-supplied 120s and
101s Retry-After values) and completed.

**Lecture summary quality read** (`--type lecture --merge`, saved to
the private archive):

- Content and structure solid — the study-notes section is close to
  shareable with light edits.
- **Timestamps unreliable:** mixed formats, some internally
  contradictory (a "~140:00" exceeding the 2h09m recording, paired with
  a non-matching seconds value). Treat all summary timestamps as
  approximate; the JSON stays the source of truth.
- **The surprise: correct participant attribution without diarization's
  help.** The summary named live-demo participants correctly (verified
  against Zoom's roster) despite the merged SPEAKER_XX labels — the LLM
  inferred identity from vocatives in the content, unprompted. That is
  the Tier 4 "speaker inference from transcript content" pattern
  occurring in the wild, and it answers the scoping question for
  instructional sessions; whether OLC meeting types talk the same way
  is still open (probe queued). Logged as evidence in WATERSHED.

**ESIIL naming — a correction to the quality read, and a lesson:** the
summary's "Environmental Data Science Innovation and Impact Lab" was
flagged as an error against the course director's email signature
("Innovation and Inclusion Lab"). Jason's correction: both are real —
the lab was originally the Innovation and *Inclusion* Lab and was
renamed to Innovation and *Impact* Lab in recent years. So the
transcript/summary was right and the "ground truth" signature was the
stale artifact. Lesson for verification tooling generally: reference
data ages; institutional names can legitimately vary by era, and a
sanity-check false positive can come from the *checker's* side of the
comparison.

**WATERSHED additions:** speaker-identity reference-signal taxonomy
(five options, cheapest-first: named VTT transfer → roster seeding →
roll-call protocol → video-frame OCR → voice embeddings) parked next to
the Tier 4 cluster, folding in Jason's seeding and mp4-frame ideas.

**Day's results in one paragraph:** the pipeline survived first contact
with a 2h09m, 11-speaker, real-world recording — one real bug found and
fixed in the API path (429 retry), one guidance miscalibration found
and logged (`--max_speakers` pinning on large sessions), the deferred
Zoom-baseline comparison run and scored (93.5% content agreement;
science-word claim supported but narrow; both systems mangled spoken
"ESIIL"), speaker-name transfer proven at ~99.7% vote share with
self-flagging, a usable lecture summary produced, and unexpected
in-the-wild evidence for the Tier 4 LLM-inference idea. The repo also
gained the retry fix, five tests, and three known-terms entries along
the way.
