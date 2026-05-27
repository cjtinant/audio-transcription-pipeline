# Audio Transcription Pipeline

A local, private, free pipeline for transcribing multi-speaker audio recordings
and generating AI summaries. Built on WhisperX + pyannote for speaker-aware
transcription, with support for both local (Ollama) and cloud (Anthropic API)
summarization.

**What it does:**

- Transcribes audio to text with accurate word-level timestamps
- Identifies who is speaking at each moment (speaker diarization)
- Generates structured summaries tailored to your meeting type
- Saves both the full transcript and summary to disk automatically

**Supported meeting types:** General meeting, standup, interview, research
conversation, lecture, or custom prompt

**Supported platforms:** macOS (Apple Silicon), macOS (Intel), Windows (WSL2),
Linux

**Privacy:** This pipeline is designed so that your audio and transcripts never
have to leave your computer. The transcription step (WhisperX + pyannote) runs
entirely locally — no audio is uploaded anywhere, ever.

For the summarization step you have two options:

- **Ollama (default)** — runs a local AI model on your own machine. Nothing
  leaves your computer. Free, private, and works offline. Recommended for
  sensitive recordings: interviews, clinical conversations, confidential
  meetings, or anything you would not want stored on a third-party server.

- **Anthropic API** — sends the text transcript (not the audio) to Anthropic's
  servers for summarization. Faster and higher quality, but your transcript
  content is processed externally. Review
  [Anthropic's privacy policy](https://www.anthropic.com/privacy) before using
  this option with sensitive material.

In both cases, your audio file stays on your machine.

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
  output/meeting.json
       │
       │  a structured file containing every segment: who said what, when
       ▼
Step 2 — Summarize (R or Python)
  source("transcribe.R")
  result <- run_pipeline("output/meeting.json")
       │
       │  R reads the JSON, formats it, sends it to an LLM
       │  LLM returns a structured summary
       ▼
  output/meeting_transcript_20260502.txt
  output/meeting_summary_20260502.txt
```

**Why two steps instead of one?**

- **Step 1 is slow and runs once.** Transcribing a 1-hour recording takes a few
  minutes. The JSON output is saved so you never have to re-transcribe the same
  file.

- **Step 2 is fast and runs many times.** Once you have the JSON, you can
  summarize it with different meeting types, different models, or different
  prompts in seconds — without touching the audio again.

- **They are independent by design.** The terminal step (WhisperX) and the
  summarization step (R or Python) do not depend on each other being open or
  running. If one fails, the other is unaffected. This also means R users and
  Python users can share the same JSON output and run their own summarization
  step independently.

**The files and what they do:**

| File                      | Role                                     | When you touch it                 |
| ------------------------- | ---------------------------------------- | --------------------------------- |
| `transcribe.sh`           | Runs WhisperX on any audio file          | Step 1 — once per recording       |
| `transcribe.R`            | Reads JSON, summarizes via R             | Step 2 — R users                  |
| `transcribe.py`           | Reads JSON, summarizes via Python or CLI | Step 2 — Python users             |
| `output/*.json`           | WhisperX output — intermediate file      | Created in Step 1, read in Step 2 |
| `output/*_transcript.txt` | Clean readable transcript                | Created in Step 2                 |
| `output/*_summary.txt`    | LLM summary                              | Created in Step 2                 |

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
cd ~/audio-transcription-pipeline
source .venv/bin/activate
.venv/bin/whisperx "/full/path/to/your/meeting.m4a" \
  --model large-v2 \
  --diarize \
  --hf_token "$(grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/audio-transcription-pipeline/output \
  --language en
```

**For Zoom recordings on macOS**, your files are in `~/Documents/Zoom/`. Zoom
folder names always contain spaces — always wrap the path in quotes:

```bash
transcribe "~/Documents/Zoom/2026-05-22 13.06.45 Meeting Name/audio.m4a"
```

Output saved to: `~/audio-transcription-pipeline/output/audio.json`

---

### Speaker count tuning (diarization quality)

By default, pyannote auto-detects how many speakers are present. Auto-detection
works well for 1–2 speakers but degrades with 3 or more speakers, or when
speakers have similar voices or talk over each other.

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

### Step 2 — Summarize (R)

Open Positron or RStudio, set your working directory to the repo, then:

```r
source("~/audio-transcription-pipeline/transcribe.R")

# Choose your meeting type: general, standup, interview, research, lecture
result <- run_pipeline(
  "~/audio-transcription-pipeline/output/audio1234567.json",
  engine       = "anthropic",   # or "ollama" for local/free
  meeting_type = "lecture"      # match to your recording type
)
```

Outputs saved automatically to `~/audio-transcription-pipeline/output/`:

- `audio1234567_transcript_20260507_130000.txt`
- `audio1234567_summary_20260507_130000.txt`

---

### Step 2 — Summarize (Python CLI)

```bash
cd ~/audio-transcription-pipeline
source .venv/bin/activate

python transcribe.py output/audio1234567.json \
  --engine anthropic \
  --type lecture
```

---

### Before you start — checklist

- [ ] Ollama is running in a separate terminal (`ollama serve`) if using local
      summarization
- [ ] `~/.Renviron` contains `HF_TOKEN` and optionally `ANTHROPIC_API_KEY`
- [ ] The venv is activated before calling whisperx

---

## Documentation

- [docs/installation.md](docs/installation.md) — Security, platform setup,
  HuggingFace tokens, testing your install, troubleshooting
- [docs/reference.md](docs/reference.md) — R and Python API reference, meeting
  type presets, LLM backend options
- [docs/noise-reduction.md](docs/noise-reduction.md) — Pre-processing options
  for poor-quality audio

---

## Project Structure

```
audio-transcription-pipeline/
├── .gitignore           # Excludes credentials, audio files, JSON output
├── README.md            # This file — daily use
├── transcribe.R         # R pipeline (Step 2 — R users)
├── transcribe.py        # Python pipeline (Step 2 — Python users)
├── transcribe.sh        # Bash wrapper for WhisperX (Step 1)
├── docs/
│   ├── installation.md  # Setup instructions for all platforms
│   ├── reference.md     # R/Python API reference and LLM options
│   └── noise-reduction.md
└── output/              # Transcripts and summaries saved here (gitignored)
    └── .gitkeep
```

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

In the interest of transparency about how the project was built, and flagging
the AI-assisted authorship as relevant context for anyone who wants to
contribute, extend, or evaluate the work:

This project was written by
[Claude Sonnet 4.6](https://www.anthropic.com/claude) (Anthropic) in
collaboration with a faculty-member at a Tribal College whose current research
interests are statistical hydrology and surface-water quality — and not a
software developer. The architecture, use case, and design decisions are
human-originated; the code is AI-generated.

The intended user is a researcher or practitioner who works with recorded
conversations — interviews, meetings, lectures — and wants a local, private
transcription workflow.
