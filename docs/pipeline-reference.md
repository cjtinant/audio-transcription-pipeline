# Pipeline Reference

Python API reference, meeting type presets, and LLM backend options.

---

## Running the Pipeline

### Step 1 — Transcribe your audio file

**After installing the `transcribe` script:**

```bash
transcribe /path/to/your/meeting.m4a
```

**Or call WhisperX directly:**

```bash
source .venv/bin/activate

whisperx /path/to/your/meeting.m4a \
  --model large-v3 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/PROJECTS/audio-transcription-output \
  --language en
```

Output: `~/PROJECTS/audio-transcription-output/meeting.json`

**Optional flags:**

- `--min_speakers 2 --max_speakers 4` — constrain speaker count if known
- `--language fr` — specify language (default: auto-detect)
- `--model medium` — use smaller model for speed (less accurate)

### Step 2 — Generate summary

```bash
# Anthropic API — default
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json

# Local Ollama
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --engine ollama

# With meeting type preset
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type interview

# List available meeting types
python summarize_transcript.py --list-types
```

Outputs saved automatically to `~/PROJECTS/audio-transcription-output/` (the
default `output_dir` — no need to pass it explicitly):

- `meeting_transcript_20260502_175200.txt`
- `meeting_summary_20260502_175200.txt`

---

## Python Pipeline Reference

### Installation

The Python script requires `httpx` for API calls. Install it into the existing
venv:

```bash
source .venv/bin/activate
uv pip install httpx
```

### CLI usage

```bash
# Basic — Anthropic API (default), general meeting type
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json

# Local Ollama
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --engine ollama

# Meeting type preset
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type interview

# Custom prompt
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type custom \
    --prompt "List every action item and who owns it."

# Override the Anthropic model (default is claude-opus-5)
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json \
    --model claude-sonnet-5   # faster/cheaper

# Multi-hour lecture or course session — raise the output ceiling if the
# summary looks cut off mid-section
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/lecture.json \
    --type lecture --max-tokens 16000

# Override the Ollama model
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json \
    --engine ollama --model llama3.1:8b-instruct-q8_0

# Skip saving to disk
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --no-save

# List available meeting types
python summarize_transcript.py --list-types
```

### Interactive / script usage

Import it like any module — run Python from the repo folder (or add the repo to
`sys.path` first):

```python
from summarize_transcript import run_pipeline

# Anthropic API (default), general meeting
result = run_pipeline("~/PROJECTS/audio-transcription-output/meeting.json")

# Local Ollama, interview preset
result = run_pipeline("~/PROJECTS/audio-transcription-output/interview.json",
                      engine="ollama",
                      meeting_type="interview")

# Custom prompt
result = run_pipeline("~/PROJECTS/audio-transcription-output/meeting.json",
                      meeting_type="custom",
                      custom_prompt="List every number mentioned.")

# Override model
result = run_pipeline("~/PROJECTS/audio-transcription-output/meeting.json",
                      model="llama3.1:8b-instruct-q8_0")

# Multi-hour lecture — lecture preset, larger output ceiling
result = run_pipeline("~/PROJECTS/audio-transcription-output/lecture.json",
                      meeting_type="lecture",
                      max_tokens=16000)
```

For most interactive use, the CLI usage above is simpler — this is only needed
if you want `run_pipeline`'s return value (segments, transcript, summary)
available directly in a Python session or another script.

**Access results programmatically:**

```python
result["segments"]    # list of dicts: start, end, speaker, text
result["transcript"]  # formatted string
result["summary"]     # LLM summary string
result["paths"]       # dict of saved file paths (if save=True)
```

---

## Running the Tests

Unit tests cover the pure functions (parsing, report building, timestamp
matching) across all four Python tools. No LLM is called and no audio is needed
— standard library `unittest` only, nothing extra to install:

```bash
cd ~/PROJECTS/audio-transcription-pipeline
python3 -m unittest discover tests
```

---

## Meeting Type Presets

| Type             | Best for                               | Output includes                                         |
| ---------------- | -------------------------------------- | ------------------------------------------------------- |
| `general`        | Team meetings, calls                   | Overview, decisions, action items, open questions       |
| `standup`        | Daily standups                         | Completed work, today's plan, blockers per speaker      |
| `interview`      | Research interviews, user interviews   | Themes, insights, notable quotes, follow-ups            |
| `research`       | Academic discussions, lab meetings     | Research question, findings, methods, next steps        |
| `lecture`        | Lectures, presentations, webinars      | Topics, key concepts with timestamps, study notes       |
| `grant_planning` | Grant proposals, funding conversations | Opportunities, decisions, risks, action items, timeline |
| `custom`         | Anything else                          | Whatever your prompt specifies                          |

**Custom prompt example:**

```bash
python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json \
  --type custom \
  --prompt "You are summarizing a grant planning meeting. Extract: funding opportunities discussed, deadlines mentioned, assigned responsibilities, and budget considerations."
```

---

## LLM Backend Options

### Anthropic API (Cloud) — default

Requires an [Anthropic account](https://console.anthropic.com) and API key.
Transcript text (not audio) is sent to Anthropic's servers — do not use for
sensitive/confidential recordings without reviewing their data policy, or use
the Ollama option below instead. Chosen as the default after a real engine
comparison (2026-07-12, logged in `WATERSHED.md`) found it noticeably more
reliable than Ollama's local model for LLM-based transcript review — not just
faster, but more likely to follow output-format instructions exactly and less
prone to false-positive flags.

**Pricing (verified 2026-07-24, per million tokens):**

| Model              | Input  | Output | Notes                            |
| ------------------ | ------ | ------ | -------------------------------- |
| `claude-haiku-4-5` | $1.00  | $5.00  | Fastest; 200k context, not 1M    |
| `claude-sonnet-5`  | $3.00  | $15.00 | $2/$10 intro through 2026-08-31  |
| `claude-opus-5`    | $5.00  | $25.00 | **Default** — freshest knowledge |
| `claude-fable-5`   | $10.00 | $50.00 | Frontier reasoning; slower       |

**Why `claude-opus-5` is the default:** this pipeline's hard case is a
multi-hour lecture or course session, where the summary depends on holding the
whole transcript in view and noticing structure across it. Opus 5 also has the
freshest knowledge cutoff of the current lineup, which matters when a recording
references recent tools or events. See
`docs/references/cowork-model-selection.md` for the fuller comparison.

This is a reasoned default, not a measured one — no A/B comparison has been run
across Claude models for this task, unlike the Anthropic-vs-Ollama engine
decision (WATERSHED 2026-07-12).

**Rough cost per 1-hour meeting summary:** ~$0.10 on Opus 5 (~14k input tokens,
~2k output). A 3-hour lecture with `--merge` runs three requests over ~40k input
tokens each — closer to $0.75. Both are estimates from token arithmetic, not
measured invoices.

**Output length:** `--max-tokens` (default 8192) caps the summary. The previous
value of 1024 silently truncated long summaries mid-section; if a summary still
stops abruptly, raise this rather than assuming the model had nothing more to
say.

```bash
# Add to ~/.Renviron
echo 'ANTHROPIC_API_KEY=sk-ant-yourkey' >> ~/.Renviron
```

Default — no `--engine` flag needed.

### Ollama (Local — Free, Private)

Runs entirely on your machine. No data leaves your computer. Requires
[Ollama](https://ollama.com) to be installed and running. Use this for sensitive
recordings you don't want processed by a third-party server — the tradeoff is
lower reliability, per the same engine comparison above.

```bash
# Install Ollama
# macOS: download from https://ollama.com
# Linux / WSL2 Ubuntu:
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b-instruct-q6_k   # recommended (6.6GB)
ollama pull llama3.1:8b-instruct-q8_0   # higher quality (8.5GB)

# Start Ollama server (keep running in a separate terminal)
ollama serve
```

**WSL2 users:** install Ollama inside the WSL2 Ubuntu environment using the
command above — not the Windows installer. Your scripts connect to it at
`http://localhost:11434` with no extra configuration. If that address is
unreachable, start Ollama with `OLLAMA_HOST=0.0.0.0:11434 ollama serve` to make
it listen on all interfaces.

`--engine ollama` (Python CLI) or `engine="ollama"` (interactive/script usage).
