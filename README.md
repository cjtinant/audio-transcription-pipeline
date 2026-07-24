# Audio Transcription Pipeline

A pipeline for transcribing multi-speaker audio recordings and generating AI
summaries. Built on WhisperX + pyannote for speaker-aware transcription (always
local), with Claude (Anthropic API) as the default summarization engine and a
fully local Ollama option for sensitive recordings.

**What it does:**

- Transcribes audio to text with accurate word-level timestamps
- Identifies who is speaking at each moment (speaker diarization)
- Generates structured summaries tailored to your meeting type
- Saves both the full transcript and summary to disk automatically

**Supported meeting types:** General meeting, standup, interview, research
conversation, lecture, grant planning, or custom prompt

**Supported platforms:** macOS (Apple Silicon), macOS (Intel), Windows (WSL2),
Linux

**Privacy:** The transcription step (WhisperX + pyannote) runs entirely locally
— no audio is ever uploaded anywhere, regardless of which summarization option
you use.

The summarization step is where your choice of engine matters, since this step
sends the text transcript (never the audio) to whichever backend you pick:

- **Anthropic API (default)** — sends the transcript text to Anthropic's servers
  for summarization. Faster and noticeably more reliable in testing (see
  `WATERSHED.md`'s 2026-07-12 engine comparison). Review
  [Anthropic's privacy policy](https://www.anthropic.com/privacy) before using
  this on sensitive material.

- **Ollama (local/private)** — runs a local AI model on your own machine.
  Nothing leaves your computer. Free, private, and works offline. Use this for
  sensitive recordings: interviews, clinical conversations, confidential
  meetings, or anything you would not want processed by a third-party server.
  Pass `--engine ollama` to use it.

In both cases, your audio file stays on your machine — only the transcript text
is ever sent externally, and only if you use the Anthropic option.

---

## How It Works

This pipeline is built from two separate, independent tools that each do one job
well. Understanding this split is the key to using it confidently.

```
Step 1 — Transcribe (terminal)
  transcribe meeting.m4a
       │
       │  whisperx converts audio → text with speaker labels + timestamps
       │  pyannote identifies who is speaking at each moment
       ▼
  ~/PROJECTS/audio-transcription-output/meeting.json
       │
       ├─── quick path (no review) ──────────────────────────────────────┐
       │                                                                  │
       │  [recommended] review_transcript.py → browser                  │
       │  label speakers, flag errors, export + clean                   │
       ▼                                                                  │
  ~/PROJECTS/audio-transcription-output/meeting_clean.txt                 │
       │                                                                  │
       └──────────────────────────────────────────────────┬──────────────┘
                                                          ▼
Step 2 — Summarize
  python3 summarize_transcript.py meeting_clean.txt
       │
       │  reads transcript, sends to LLM, returns structured summary
       ▼
  ~/PROJECTS/audio-transcription-output/meeting_clean_summary_20260502_141530.txt
```

All output lands in one flat, private, local-git-backed folder outside this repo
— see [Where output goes](#where-output-goes) below.

**Why two steps instead of one?**

- **Step 1 is slow and runs once.** Transcribing a 1-hour recording takes a few
  minutes. The JSON output is saved so you never have to re-transcribe the same
  file.

- **Step 2 is fast and runs many times.** Once you have the JSON, you can
  summarize it with different meeting types, different models, or different
  prompts in seconds — without touching the audio again.

- **They are independent by design.** The terminal step (WhisperX) and the
  summarization step do not depend on each other being open or running. If one
  fails, the other is unaffected.

**Why JSON as the intermediate format?**

WhisperX can output plain text, SRT, or VTT instead — but this pipeline always
uses `--output_format json`. Flat formats collapse the transcript down to words
or captions and throw away the structure later steps depend on: JSON is the only
format that keeps word-level timestamps, per-segment speaker labels (from
diarization), and confidence scores together. `review_transcript.py` needs that
structure to build the speaker-colored view and confidence sliders, and the
summarizer's quick path reads it directly. The human-cleaned `.txt` is a
derived, simplified view for the summarizer — JSON stays the source of truth,
permanently, in the private output archive (see below).

**The files and what they do:**

| File                                                       | Role                                         | When you touch it                    |
| ---------------------------------------------------------- | -------------------------------------------- | ------------------------------------ |
| `transcribe.sh`                                            | Runs WhisperX on any audio file              | Step 1 — once per recording          |
| `review_transcript.py`                                     | JSON → interactive HTML for reviewing output | Optional — between Step 1 and Step 2 |
| `summarize_transcript.py`                                  | Reads JSON, generates LLM summary            | Step 2                               |
| `~/PROJECTS/audio-transcription-output/*.json`             | WhisperX output — permanent original record  | Created in Step 1, read in Step 2    |
| `~/PROJECTS/audio-transcription-output/*_transcript_*.txt` | Clean readable transcript                    | Created in Step 2                    |
| `~/PROJECTS/audio-transcription-output/*_summary_*.txt`    | LLM summary                                  | Created in Step 2                    |
| `~/PROJECTS/audio-transcription-output/*_review.html`      | Interactive reviewed transcript              | Created by `review_transcript.py`    |

### Where output goes

Every artifact from every recording — raw JSON, cleaned transcript, summary,
reviewed HTML — is written directly to a single folder outside this repo:
`~/PROJECTS/audio-transcription-output/`. Nothing lands inside this repo's own
directory at any point.

That folder is:

- **Flat.** No `raw/`/`processed/` subfolders. The `yyyy-mm-dd_subject-name`
  naming convention (below) already makes files findable by subject via sort or
  search — a folder hierarchy would just duplicate that.
- **Local git, no remote.** Gives version history — recover a file after a bad
  edit, an accidental deletion, or a script bug — without the data ever leaving
  your machine. It is not a substitute for disk-level backup (Time Machine, an
  external drive, etc.); local git history doesn't survive a dead drive.
- **Permanent.** No script in this pipeline ever deletes or moves files out of
  this folder. It is the private original record.
- **Private by design.** This repo is public; keeping every output artifact in a
  sibling folder entirely outside it means research transcripts can never end up
  in this repo's git history, even by accident.

If you need to share something derived from a recording — meeting notes, a
redacted summary — that's a deliberate, manual step you do yourself: edit a copy
down to what's safe to share, then move only that copy into wherever it actually
needs to go. The original stays in the archive.

The location is a default, not a requirement — export `TRANSCRIBE_OUTPUT_DIR`
to put the archive somewhere else (both `transcribe` and the summarizer honor
it). See `docs/installation.md` for one-time setup of this folder.

---

## Daily Use — Once You're Set Up

Once installed, this is all you need to transcribe and summarize any recording.
You do not need to be inside the repo folder.

### Poor audio quality?

Background noise, echo, or room reflections can hurt transcription accuracy. See
[docs/noise-reduction.md](docs/noise-reduction.md) for options ranging from a
one-click cloud tool (Adobe Podcast Enhance) to manual Audacity workflows.

---

### Starting from a video file?

If your recording is a `.mp4`, `.mov`, or other video format, extract the audio
first with ffmpeg:

```bash
ffmpeg -i your_recording.mp4 -vn audio.wav
```

The `-vn` flag drops the video stream. WhisperX works with the resulting `.wav`
directly.

---

### Naming convention

Rename the recording before transcribing:

- Folder: `yyyy-mm-dd_subject-name`
- Audio file: `yyyy-mm-dd_subject-name_audio.m4a`

_Example:_ `2026-07-07_soil-moisture/2026-07-07_soil-moisture_audio.m4a`

This isn't just tidiness. WhisperX names its output by swapping the extension on
the input filename, and the summarizer scripts carry that same basename forward.
Rename once, and the raw JSON, the cleaned transcript, and the summary all
inherit a consistent, dated name automatically — no separate renaming step
anywhere downstream.

---

### Step 1 — Transcribe (terminal, any directory)

If you installed the `transcribe` script, this is all you need:

```bash
# Works in bash or zsh
transcribe "/full/path/to/your/meeting.m4a"

# Pin speaker count for better diarization (see Speaker count tuning below)
transcribe "/full/path/to/your/meeting.m4a" --min_speakers 3 --max_speakers 3
```

Or call WhisperX directly:

```bash
cd ~/PROJECTS/audio-transcription-pipeline
source .venv/bin/activate
.venv/bin/whisperx "/full/path/to/your/meeting.m4a" \
  --model large-v3 \
  --diarize \
  --hf_token "$(grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/PROJECTS/audio-transcription-output \
  --language en
```

**For Zoom recordings on macOS**, Zoom's own default save location is
`~/Documents/Zoom/` — but that folder is iCloud-synced, which causes access
problems without an internet connection. Recordings here live in `~/Zoom/`
instead, moved there for that reason. Copy the path in Finder (right-click the
file → Copy "audio.m4a" as Pathname), then rename the folder and file to the
convention above before transcribing. Zoom folder names always contain spaces —
always wrap the path in quotes. Keep `~` outside the quotes (or use `$HOME`):
a tilde inside double quotes is not expanded, and the path fails as written.

```bash
transcribe ~/"Zoom/2026-07-07_soil-moisture/2026-07-07_soil-moisture_audio.m4a"

# Equivalent, and clearer if the whole path is pasted from Finder:
transcribe "$HOME/Zoom/2026-07-07_soil-moisture/2026-07-07_soil-moisture_audio.m4a"
```

Output saved to:
`~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json`

---

### Speaker count tuning (diarization quality)

By default, pyannote estimates how many speakers are present. In this
pipeline's own recordings (small meetings, 2–4 speakers), auto-detection has
worked well for 1–2 speakers but degraded with 3 or more, or when speakers
have similar voices or talk over each other — an observation from limited
use, not a benchmark.

**When you know the speaker count, always pin it.** This is the single highest-
impact change you can make to diarization quality:

```bash
# 3-person meeting — pin exactly
transcribe meeting.m4a --min_speakers 3 --max_speakers 3

# Interview — one interviewer, one subject
transcribe interview.m4a --min_speakers 2 --max_speakers 2

# Lecture with occasional student questions — set a range
transcribe lecture.m4a --min_speakers 1 --max_speakers 4
```

These flags pass directly through the `transcribe` function to WhisperX — no
wrapper changes needed.

**Signs diarization went wrong:** a single speaker's turn split across two
speaker labels, or two different speakers merged into one. Both improve
significantly with pinned speaker counts.

---

### Proper nouns and institution-specific terms

WhisperX may mishear acronyms, place names, and institution-specific terms — for
example transcribing "TEA-Center" as "T-Center". Use `--hotwords` to hint the
model:

```bash
transcribe meeting.m4a --hotwords "TEA-Center, pyannote, WhisperX"
```

Multiple terms are comma-separated. Hotwords improve recognition but don't
guarantee correct output — always review proper nouns in the transcript.

---

### Review the transcript (optional)

After Step 1, you can convert the JSON to a browser-based review tool before
summarizing. Open it to:

- Assign real names to speaker labels (SPEAKER_00, SPEAKER_01, …)
- Flag low-confidence words at an adjustable threshold
- Search for key terms or proper nouns
- Export a labeled plain-text transcript

```bash
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json

# --out only needed to override the default (same folder as the input)
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --out ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio_review.html
```

The HTML file opens in your browser automatically. Speaker name changes stay in
the browser — the JSON is not modified. Export the labeled text, then clean it
manually (fix mishears, proper nouns, anything the model got wrong). The cleaned
`.txt` is the recommended input to Step 2.

**Find and spot-check low-confidence words:** `--report` writes a compact text
file listing words below a confidence threshold, with timestamps:

```bash
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --report

# Lower the threshold to flag more words (default: 0.2)
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --report --threshold 0.15
```

To hear the actual audio around a flagged timestamp instead of guessing from
context, use `--clip` (requires the `.source-audio.json` sidecar `transcribe`
writes alongside the transcript):

```bash
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --clip 14:32

# Adjust how much context is clipped around the timestamp (default: 3.0s)
python3 review_transcript.py ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --clip 14:32 --clip-padding 5
```

---

### Harden your transcript (optional)

Two more optional tools sit between Step 1 and Step 2, aimed at catching
transcription errors before they reach a summary. Neither is required for
daily use — reach for them when a recording matters enough to double-check.

**Cross-model agreement (`compare_transcripts.py`)** — only useful if you
transcribed the same recording twice with different models (e.g. re-running
`transcribe --model large-v2` after your usual `large-v3` pass). Diffs the
two transcripts word-by-word and reports every disagreement with a
timestamp:

```bash
python3 compare_transcripts.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio_large-v2.json \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio_large-v3.json \
  --out ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_compare.txt
```

The agreement percentage it reports is a confidence signal, not a
correctness score — high agreement means the models mostly heard the same
thing, not that either is right. Where they disagree is where to actually
look.

**LLM plausibility pass (`sanity_check_transcript.py`)** — reads the
transcript and flags phrases that sound semantically odd, checked against
`known-terms.txt` so real vocabulary (institution names, technical terms)
isn't flagged as an error:

```bash
python3 sanity_check_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json

# Local/private option (no transcript text leaves your machine)
python3 sanity_check_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --engine ollama

# Use a custom vocabulary list instead of known-terms.txt
python3 sanity_check_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --known-terms my-terms.txt
```

As with `--report` above, flags are a signal to check manually, not
automatic corrections — expect some false positives on genuinely unusual
but correct phrasing.

---

### Choosing a meeting type

| Preset           | Best for                                       |
| ---------------- | ---------------------------------------------- |
| `general`        | Planning meetings, admin calls, anything mixed |
| `research`       | Lab discussions, methods conversations         |
| `interview`      | Qualitative data collection, 1-on-1 interviews |
| `lecture`        | Recorded talks, presentations, webinars        |
| `grant_planning` | Grant proposals, funding conversations         |
| `standup`        | Daily standups (probably never for most users) |
| `custom`         | Anything — you write the prompt                |

When in doubt, use `general`. It catches decisions, action items, and open
questions, which are useful across most meeting types.

### Step 2 — Summarize

```bash
cd ~/PROJECTS/audio-transcription-pipeline

# Merged (recommended): runs twice and merges for a more complete summary
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt \
  --type general \
  --merge

# Single run: cleaned .txt from review step
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt \
  --type general

# Quick path: raw JSON, no human review
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json \
  --type general

# Use Ollama instead (local/private)
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt \
  --engine ollama --type general
```

Output is written to `~/PROJECTS/audio-transcription-output/` by default (the
`--output-dir` flag exists only to override this).

### Long recordings (multi-hour lectures and course sessions)

The defaults are sized for these: `claude-opus-5` and an 8192-token output
ceiling. A 3-hour recording is roughly 40k input tokens once speaker labels and
timestamps are added, which fits comfortably in context — the thing that
actually breaks is summary length, not input size.

```bash
# 3-hour lecture — preset plus a larger output ceiling
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-13_esiil-course_audio.json \
  --type lecture --max-tokens 16000

# Faster and cheaper, if the recording is short or the stakes are low
.venv/bin/python3 summarize_transcript.py \
  ~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt \
  --model claude-sonnet-5
```

**If a summary stops mid-sentence or drops a section**, it hit the output
ceiling — raise `--max-tokens`. The model cannot signal this, so a truncated
summary looks like a complete one that simply had less to say.

Set `SUMMARIZE_MODEL` in your shell profile for a standing default without
passing `--model` every run:

```bash
export SUMMARIZE_MODEL=claude-sonnet-5
```

Avoid `--merge` on multi-hour recordings unless you need it — it fires three
large requests back to back and was the original cause of the rate-limit crash
logged in `WATERSHED.md` (2026-07-14). The retry logic handles it now, but it
triples both cost and wall-clock time.

---

### Before you start — checklist

- [ ] `~/PROJECTS/audio-transcription-output/` exists and is git-initialized
      (one-time setup — see `docs/installation.md`)
- [ ] `~/.Renviron` contains `HF_TOKEN` and `ANTHROPIC_API_KEY` (the default
      summarization engine)
- [ ] Ollama is running in a separate terminal (`ollama serve`) only if using
      `--engine ollama` for local/private summarization
- [ ] The venv is activated (or `.venv/bin/python3` used directly) before
      calling whisperx or the Python summarizer

---

## Documentation

- [docs/installation.md](docs/installation.md) — Security, platform setup,
  HuggingFace tokens, testing your install, troubleshooting
- [docs/pipeline-reference.md](docs/pipeline-reference.md) — Python API
  reference, meeting type presets, LLM backend options
- [docs/noise-reduction.md](docs/noise-reduction.md) — Pre-processing options
  for poor-quality audio

---

## Project Structure

```
audio-transcription-pipeline/
├── docs/
│   ├── installation.md               # Setup instructions for all platforms
│   ├── noise-reduction.md            # Pre-processing options for poor audio
│   ├── pipeline-reference.md         # Python API reference and LLM options
│   └── YYYY-MM-DD_session-notes.md   # Dated log per working session
├── tests/                       # Unit tests — python3 -m unittest discover tests
├── .gitignore                   # Excludes credentials and audio files
├── .prettierrc                  # Markdown formatting (80-col prose wrap)
├── LICENSE.md                   # PolyForm Noncommercial 1.0.0
├── Makefile                     # `make install` — symlinks transcribe.sh into ~/bin
├── README.md                    # This file — daily use
├── requirements-lock.txt        # Exact tested versions (reproducibility snapshot)
├── transcribe.sh                # Bash wrapper for WhisperX (Step 1)
├── review_transcript.py         # JSON → interactive HTML review tool (optional)
├── compare_transcripts.py       # Word-level diff between two transcripts (optional)
├── sanity_check_transcript.py   # LLM plausibility pass, flags likely mistranscriptions (optional)
├── known-terms.txt              # Vocabulary list for sanity_check_transcript.py
├── summarize_transcript.py      # Pipeline Step 2 — LLM summary
└── WATERSHED.md                 # Parked decisions, resolved history, open questions
```

`00_admin/`, `docs/references/`, `scratch.md`, and personal draft files are
intentionally excluded here — they're gitignored and stay local, not part of
the tracked structure.

There is no `output/` folder in this repo. All transcription output lives in a
separate, private, local-git folder — see
[Where output goes](#where-output-goes) above.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md) — free to use, modify, and share
for any noncommercial purpose, including use by educational institutions and
public research organizations regardless of funding source. Commercial use
requires separate permission from the author.

Required Notice: Copyright (c) 2026 C. Jason Tinant

---

## Acknowledgements

- [WhisperX](https://github.com/m-bain/whisperX) — Max Bain et al.
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) — Hervé Bredin et
  al.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — SYSTRAN
- [Ollama](https://ollama.com) — local LLM serving
- [Anthropic](https://anthropic.com) — Claude API

---

## A note on authorship

This project was written by someone who wanted to tackle a problem that needed
solving and decided to be FAIR and CARE using
[Claude models](https://www.anthropic.com/claude) (Anthropic) e.g. the general
architecture, use case, and design decisions are human-originated; the code and
docs are AI-generated.
