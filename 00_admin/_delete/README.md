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
| `transcribe.fish`         | Runs WhisperX on any audio file          | Step 1 — once per recording       |
| `transcribe.R`            | Reads JSON, summarizes via R             | Step 2 — R users                  |
| `transcribe.py`           | Reads JSON, summarizes via Python or CLI | Step 2 — Python users             |
| `output/*.json`           | WhisperX output — intermediate file      | Created in Step 1, read in Step 2 |
| `output/*_transcript.txt` | Clean readable transcript                | Created in Step 2                 |
| `output/*_summary.txt`    | LLM summary                              | Created in Step 2                 |

---

## Daily Use — Once You're Set Up

Once installed, this is all you need to transcribe and summarize any recording.
You do not need to be inside the repo folder.

### Step 1 — Transcribe (terminal, any directory)

```fish
# macOS fish shell — pass the full path to any audio file
cd ~/audio-transcription-pipeline
source .venv/bin/activate.fish
.venv/bin/whisperx "/full/path/to/your/meeting.m4a" \
  --model large-v2 \
  --diarize \
  --hf_token (grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r') \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/audio-transcription-pipeline/output \
  --language en
```

**For Zoom recordings on macOS**, your files are in `~/Documents/Zoom/`. Pass
the full path:

```fish
cd ~/audio-transcription-pipeline
source .venv/bin/activate.fish
.venv/bin/whisperx ~/Documents/Zoom/2026-05-07*/audio*.m4a \
  --model large-v2 \
  --diarize \
  --hf_token (grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r') \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/audio-transcription-pipeline/output \
  --language en
```

> **Note:** If the folder name has spaces or parentheses (Zoom folders always
> do), wrap the path in quotes:
> `"/Users/yourname/Documents/Zoom/2026-05-07 13.06.45 Name/audio.m4a"`

Output saved to: `~/audio-transcription-pipeline/output/audio.json`

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
source .venv/bin/activate  # or activate.fish

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

## Table of Contents

1. [Daily Use — Once You're Set Up](#daily-use--once-youre-set-up)
2. [Security First](#security-first)
3. [Quick Start — Simple Instructions](#quick-start--simple-instructions)
   - [macOS Apple Silicon](#macos-apple-silicon-simple)
   - [macOS Intel](#macos-intel-simple)
   - [Windows](#windows-simple)
   - [Linux](#linux-simple)
4. [Technical Setup](#technical-setup)
   - [macOS Apple Silicon](#macos-apple-silicon-technical)
   - [macOS Intel](#macos-intel-technical)
   - [Windows WSL2](#windows-wsl2-technical)
   - [Linux](#linux-technical)
5. [HuggingFace Setup](#huggingface-setup)
6. [Testing Your Setup](#testing-your-setup)
7. [Running the Pipeline](#running-the-pipeline)
8. [R Pipeline Reference](#r-pipeline-reference)
9. [Python Pipeline Reference](#python-pipeline-reference)
10. [Meeting Type Presets](#meeting-type-presets)
11. [LLM Backend Options](#llm-backend-options)
12. [Troubleshooting](#troubleshooting)

---

## Security First

**Your API tokens must never appear in code or be committed to git.**

This repo's `.gitignore` is configured to exclude credential files, audio files,
and output files. Before doing anything else:

1. Never paste a token into any `.R`, `.py`, or `.fish` file
2. Never commit `.Renviron` or `.env` files
3. Store all tokens in `~/.Renviron` (R reads this automatically at startup)
4. If you accidentally expose a token, invalidate it immediately at the
   provider's website and generate a new one

```bash
# Correct way to store tokens — in your home directory, not in the repo
echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron
echo 'ANTHROPIC_API_KEY=sk-ant-yourkey' >> ~/.Renviron
```

---

## Quick Start — Simple Instructions

These instructions assume you can copy and paste commands into a terminal. On
Mac, open **Terminal** (search for it with Cmd+Space). On Windows, follow the
WSL2 setup first, then use the Ubuntu terminal.

### macOS Apple Silicon (Simple)

> For MacBook Pro/Air/Mac Mini with M1, M2, M3, or M4 chip.

**Step 1 — Install Homebrew (Mac package manager)**

Open Terminal and paste:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. When it finishes, paste:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
source ~/.zprofile
```

**Step 2 — Install required tools**

```bash
brew install uv ffmpeg git
```

**Step 3 — Clone this repo and set up the environment**

```bash
git clone https://github.com/your-username/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio
uv pip install whisperx
```

**Step 4 — Set up HuggingFace** (see [HuggingFace Setup](#huggingface-setup))

**Step 5 — Install R packages**

Open R or RStudio and run:

```r
install.packages(c("jsonlite", "httr2"))
```

**Step 6 — Test it**

```bash
source .venv/bin/activate
curl -L "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" -o test.wav
whisperx test.wav \
  --model large-v2 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ./output \
  --language en
```

---

### macOS Intel (Simple)

> For older MacBook Pro/Air with Intel processor (pre-2021).

Same as Apple Silicon above, with two differences:

- Homebrew installs to `/usr/local` instead of `/opt/homebrew`. The install
  script handles this automatically.
- Replace the shellenv line in Step 1 with:
  ```bash
  echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
  source ~/.zprofile
  ```
- In Step 3, use `--compute_type int8` (same as above — Intel Macs use CPU)

Everything else is identical.

---

### Windows (Simple)

> Windows requires WSL2 (Windows Subsystem for Linux). This is a free Microsoft
> feature that gives you a full Linux environment inside Windows. It is the
> recommended approach for this pipeline.

**Step 1 — Enable WSL2**

Open PowerShell as Administrator (right-click Start → Windows PowerShell
(Admin)):

```powershell
wsl --install
```

Restart your computer when prompted. After restart, Ubuntu will open and ask you
to create a username and password — do this.

**Step 2 — Open Ubuntu terminal**

Search for "Ubuntu" in the Start menu and open it. All remaining steps run
inside this Ubuntu terminal.

**Step 3 — Install required tools**

```bash
sudo apt update && sudo apt install -y git ffmpeg python3-pip curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

**Step 4 — Clone repo and set up environment**

```bash
git clone https://github.com/your-username/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
```

**Step 5 — Set up HuggingFace** (see [HuggingFace Setup](#huggingface-setup))

**Step 6 — Install R**

In the Ubuntu terminal:

```bash
sudo apt install -y r-base
```

Then start R with `R` and install packages:

```r
install.packages(c("jsonlite", "httr2"))
```

---

### Linux (Simple)

> Tested on Ubuntu 22.04+. Other distributions follow the same pattern.

```bash
# Install system dependencies
sudo apt update && sudo apt install -y git ffmpeg python3-pip curl

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and set up
git clone https://github.com/your-username/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx

# Install R packages
R -e 'install.packages(c("jsonlite", "httr2"), repos="https://cloud.r-project.org")'
```

If you have an NVIDIA GPU, replace the torch install with:

```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

And use `--device cuda --compute_type float16` when running WhisperX.

---

## Technical Setup

### macOS Apple Silicon (Technical)

**Requirements:** macOS 13+, Homebrew at `/opt/homebrew`, uv, fish or zsh

```fish
# Verify ARM Homebrew
file $(which brew)
# Expected: Bourne-Again shell script text executable

# Install tools
brew install uv ffmpeg git

# Create project venv with ARM-native Python 3.11
cd ~/audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate.fish  # or: source .venv/bin/activate for zsh/bash

# Install PyTorch (CPU — MPS experimental, CPU+int8 is reliable)
uv pip install torch torchaudio
uv pip install whisperx

# Verify ARM architecture
python3 -c "import torch; print(torch.__version__)"
file .venv/bin/python3
# Expected: Mach-O 64-bit executable arm64
```

**Note on Metal/MPS:** WhisperX uses `faster-whisper` which does not yet support
MPS natively. CPU + int8 quantization on Apple Silicon with 16GB+ unified memory
is fast and reliable. large-v2 transcribes at ~10-15x realtime on M1 Max.

**fish shell one-command setup:**

```fish
cp transcribe.fish ~/.config/fish/functions/transcribe.fish
source ~/.config/fish/config.fish
# Usage: transcribe mymeeting.m4a
```

---

### macOS Intel (Technical)

Same as Apple Silicon with these differences:

- Homebrew root: `/usr/local`
- Python architecture: `x86_64` (not arm64)
- PyTorch install: same CPU wheels work on Intel
- Performance: ~3-5x slower than Apple Silicon for large-v2

```bash
# Verify Homebrew location
which brew  # should be /usr/local/bin/brew
brew install uv ffmpeg git

cd ~/audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio
uv pip install whisperx
```

---

### Windows WSL2 (Technical)

WSL2 runs a real Linux kernel via Hyper-V. Performance is near-native for CPU
workloads. GPU passthrough requires WSL2 + CUDA drivers (NVIDIA only).

```powershell
# PowerShell (Admin) — install WSL2 with Ubuntu 22.04
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

In Ubuntu terminal:

```bash
# System deps
sudo apt update && sudo apt install -y \
  git ffmpeg python3-pip curl build-essential

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone
git clone https://github.com/your-username/audio-transcription-pipeline.git
cd audio-transcription-pipeline

# Venv
uv venv --python 3.11 .venv
source .venv/bin/activate

# PyTorch CPU (default for WSL2 without NVIDIA GPU)
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
```

**Audio files on Windows:** Your Windows files are accessible at
`/mnt/c/Users/YourName/`. Copy audio files to your WSL2 home first:

```bash
cp /mnt/c/Users/YourName/Downloads/meeting.m4a ~/audio-transcription-pipeline/
```

**Tokens in WSL2:** Add to `~/.bashrc` (WSL2 doesn't use `~/.Renviron` unless
you install R inside WSL2):

```bash
echo 'export HF_TOKEN=hf_yourtoken' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY=sk-ant-yourkey' >> ~/.bashrc
source ~/.bashrc
```

**NVIDIA GPU in WSL2:** Install CUDA-enabled PyTorch:

```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Then use `--device cuda --compute_type float16` with WhisperX.

---

### Linux (Technical)

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y \
  git ffmpeg python3-pip curl build-essential

# RHEL/Fedora
sudo dnf install -y git ffmpeg python3-pip curl gcc

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and set up
git clone https://github.com/your-username/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate

# CPU only
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx

# NVIDIA GPU (CUDA 12.4)
# uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
# Use: --device cuda --compute_type float16
```

---

## HuggingFace Setup

WhisperX uses pyannote models for speaker diarization. These are gated (require
a free account and license agreement).

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Go to **Settings → Access Tokens → New token**
3. Select the **Read** tab, name it `whisperx-local`, click **Create**
4. Copy the `hf_...` token — you only see it once
5. Accept the license on both model pages (must be logged in):
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
   - [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)
6. Add the token to your credentials file:

**macOS/Linux (R users):**

```bash
echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron
```

**Windows WSL2:**

```bash
echo 'export HF_TOKEN=hf_yourtoken' >> ~/.bashrc
source ~/.bashrc
```

> ⚠️ If you ever accidentally paste your token into a file that gets committed
> to git, go to huggingface.co/settings/tokens immediately, invalidate the
> token, and generate a new one.

---

## Testing Your Setup

Before using your own audio, verify the full pipeline works end-to-end using a
free public domain speech sample. Run these steps in order after completing
setup and HuggingFace configuration.

### Step 1 — Download the test audio

This is a ~32 second phonetics test recording (Harvard Sentences) — a single
speaker, clean audio, ideal for verifying transcription works.

```bash
cd ~/audio-transcription-pipeline
curl -L "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" \
  -o test.wav
```

### Step 2 — Activate the environment and transcribe

```bash
# bash/zsh
source .venv/bin/activate

# fish shell
source .venv/bin/activate.fish
```

```bash
whisperx test.wav \
  --model large-v2 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ./output \
  --language en
```

This will download models on first run (~3.5GB total). Subsequent runs use
cached models and are much faster.

**Expected output:**

```
Performing voice activity detection using Pyannote...
Performing transcription...
Transcript: [0.031 --> 28.921]  The birch canoe slid on the smooth planks...
Performing alignment...
Performing diarization...
```

Output file: `output/test.json`

### Step 3 — Verify in R

```r
source("transcribe.R")

result <- run_pipeline(
  "output/test.json",
  engine = "ollama",    # or "anthropic" if you have an API key
  save   = FALSE        # skip saving for this test run
)
```

**Expected transcript output:**

```
[SPEAKER_00 @ 0.5s] The birch canoe slid on the smooth planks.
[SPEAKER_00 @ 4.3s] Glued the sheet to the dark blue background.
...
```

**Expected summary output** (will note no decisions/action items since this is a
phonetics test, not a real meeting — that is correct behavior):

```
Key Decisions Made: None apparent from the transcript.
Action Items: None apparent from the transcript.
```

✅ If you see the transcript and summary, your pipeline is working correctly.

### Step 4 — Clean up test files

```bash
rm test.wav output/test.json
```

> Note: `test.wav` and `output/*.json` are excluded by `.gitignore` — they will
> never be accidentally committed to the repo.

---

## Running the Pipeline

### Step 1 — Transcribe your audio file

**macOS/Linux (fish shell, after installing the fish function):**

```fish
transcribe /path/to/your/meeting.m4a
```

**Any platform (direct command):**

```bash
source .venv/bin/activate  # or activate.fish for fish shell

whisperx /path/to/your/meeting.m4a \
  --model large-v2 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ./output \
  --language en
```

Output: `output/meeting.json`

**Optional flags:**

- `--min_speakers 2 --max_speakers 4` — constrain speaker count if known
- `--language fr` — specify language (default: auto-detect)
- `--model medium` — use smaller model for speed (less accurate)

### Step 2 — Generate summary

**R (primary — recommended for R users):**

```r
source("transcribe.R")

# Local Ollama (free, private, requires Ollama running)
result <- run_pipeline("output/meeting.json")

# Anthropic API (requires ANTHROPIC_API_KEY in ~/.Renviron)
result <- run_pipeline("output/meeting.json", engine = "anthropic")

# With meeting type preset
result <- run_pipeline("output/meeting.json",
                       engine       = "anthropic",
                       meeting_type = "interview")
```

**Python (CLI — recommended for Python users):**

```bash
# Local Ollama
python transcribe.py output/meeting.json

# Anthropic API
python transcribe.py output/meeting.json --engine anthropic

# With meeting type preset
python transcribe.py output/meeting.json --engine anthropic --type interview

# List available meeting types
python transcribe.py --list-types
```

Outputs saved automatically to `output/`:

- `meeting_transcript_20260502_175200.txt`
- `meeting_summary_20260502_175200.txt`

---

## R Pipeline Reference

```r
run_pipeline(
  json_path,              # Path to WhisperX JSON output
  engine       = "ollama",    # "ollama" or "anthropic"
  meeting_type = "general",   # See Meeting Type Presets below
  custom_prompt = NULL,       # Your own prompt (if meeting_type = "custom")
  save         = TRUE,        # Save outputs to disk
  output_dir   = "output",    # Output directory
  ...                         # Passed to summarize_ollama() or
                              # summarize_anthropic() — e.g., model = "..."
)
```

**Change the Ollama model:**

```r
result <- run_pipeline("output/meeting.json",
                       model = "llama3.1:8b-instruct-q8_0")
```

**Change the Anthropic model:**

```r
result <- run_pipeline("output/meeting.json",
                       engine = "anthropic",
                       model  = "claude-haiku-4-5")  # cheaper/faster
```

**Access results programmatically:**

```r
result$segments    # data frame: start, end, speaker, text
result$transcript  # formatted string
result$summary     # LLM summary string
result$paths       # list of saved file paths
```

---

## Python Pipeline Reference

### Installation

The Python script requires `httpx` for API calls. Install it into the existing
venv:

```bash
source .venv/bin/activate  # or activate.fish
uv pip install httpx
```

### CLI usage

```bash
# Basic — local Ollama, general meeting type
python transcribe.py output/meeting.json

# Anthropic API
python transcribe.py output/meeting.json --engine anthropic

# Meeting type preset
python transcribe.py output/meeting.json --type interview

# Custom prompt
python transcribe.py output/meeting.json --type custom \
    --prompt "List every action item and who owns it."

# Override model
python transcribe.py output/meeting.json \
    --model llama3.1:8b-instruct-q8_0

# Skip saving to disk
python transcribe.py output/meeting.json --no-save

# List available meeting types
python transcribe.py --list-types
```

### Interactive / script usage

```python
from transcribe import run_pipeline

# Local Ollama, general meeting (default)
result = run_pipeline("output/meeting.json")

# Anthropic API, interview preset
result = run_pipeline("output/interview.json",
                      engine="anthropic",
                      meeting_type="interview")

# Custom prompt
result = run_pipeline("output/meeting.json",
                      meeting_type="custom",
                      custom_prompt="List every number mentioned.")

# Override model
result = run_pipeline("output/meeting.json",
                      model="llama3.1:8b-instruct-q8_0")
```

**Access results programmatically:**

```python
result["segments"]    # list of dicts: start, end, speaker, text
result["transcript"]  # formatted string
result["summary"]     # LLM summary string
result["paths"]       # dict of saved file paths (if save=True)
```

---

## Meeting Type Presets

| Type        | Best for                             | Output includes                                    |
| ----------- | ------------------------------------ | -------------------------------------------------- |
| `general`   | Team meetings, calls                 | Overview, decisions, action items, open questions  |
| `standup`   | Daily standups                       | Completed work, today's plan, blockers per speaker |
| `interview` | Research interviews, user interviews | Themes, insights, notable quotes, follow-ups       |
| `research`  | Academic discussions, lab meetings   | Research question, findings, methods, next steps   |
| `lecture`   | Lectures, presentations, webinars    | Topics, key concepts with timestamps, study notes  |
| `custom`    | Anything else                        | Whatever your prompt specifies                     |

**Custom prompt example:**

```r
result <- run_pipeline(
  "output/meeting.json",
  meeting_type  = "custom",
  custom_prompt = paste0(
    "You are summarizing a grant planning meeting. ",
    "Extract: funding opportunities discussed, ",
    "deadlines mentioned, assigned responsibilities, ",
    "and budget considerations.\n\nTranscript:\n"
  )
)
```

---

## LLM Backend Options

### Ollama (Local — Free, Private)

Runs entirely on your machine. No data leaves your computer. Requires
[Ollama](https://ollama.com) to be installed and running.

```bash
# Install Ollama
# macOS: download from https://ollama.com
# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b-instruct-q6_k   # recommended (6.6GB)
ollama pull llama3.1:8b-instruct-q8_0   # higher quality (8.5GB)

# Start Ollama server (keep running in a separate terminal)
ollama serve
```

In R: `engine = "ollama"` (default)

### Anthropic API (Cloud)

Requires an [Anthropic account](https://console.anthropic.com) and API key. Data
is sent to Anthropic's servers — do not use for sensitive/confidential
recordings without reviewing their data policy.

**Pricing (May 2026, per million tokens):**

| Model               | Input | Output | Notes               |
| ------------------- | ----- | ------ | ------------------- |
| `claude-haiku-4-5`  | $1.00 | $5.00  | Fastest, cheapest   |
| `claude-sonnet-4-6` | $3.00 | $15.00 | Recommended balance |
| `claude-opus-4-6`   | $5.00 | $25.00 | Highest quality     |

**Typical cost per 1-hour meeting summary:** ~$0.035 (Sonnet 4.6)

```bash
# Add to ~/.Renviron
echo 'ANTHROPIC_API_KEY=sk-ant-yourkey' >> ~/.Renviron
```

In R: `engine = "anthropic"`

---

## Troubleshooting

**`whisperx: command not found` even after activating the venv** Use the full
path to the whisperx binary instead:

```fish
.venv/bin/whisperx your_audio.m4a ...
```

This happens because some terminals (Positron, fish) don't always add the venv
`bin/` to PATH after activation. The full path always works.

**`whisperx: command not found`** The virtual environment is not activated.

```bash
source .venv/bin/activate       # bash/zsh
source .venv/bin/activate.fish  # fish
```

**`GatedRepoError: 403`** You haven't accepted the pyannote model licenses, or
your HF token is wrong.

- Visit the two model pages and click Agree (must be logged in)
- Verify your token: `grep HF_TOKEN ~/.Renviron`

**`ANTHROPIC_API_KEY not set`** Restart R after adding the key to `~/.Renviron`
— R only reads it at startup.

**`could not find function "run_pipeline"`** Source the script first:
`source("transcribe.R")`

**Ollama connection refused** Start the Ollama server in a separate terminal:
`ollama serve`

**Poor diarization (speakers mixed up)** Add speaker count hints:

```bash
whisperx meeting.m4a --diarize --min_speakers 2 --max_speakers 2 ...
```

**Slow transcription**

- Use a smaller model: `--model medium` or `--model base`
- Reduce batch size: `--batch_size 4`
- On Linux with NVIDIA GPU: use `--device cuda --compute_type float16`

---

## Project Structure

```
audio-transcription-pipeline/
├── .gitignore           # Excludes credentials, audio files, JSON output
├── README.md            # This file
├── transcribe.R         # R pipeline (primary — R users)
├── transcribe.py        # Python pipeline (Python users — CLI + interactive)
├── transcribe.fish      # Fish shell one-command wrapper
└── output/              # Transcripts and summaries saved here (gitignored)
    └── .gitkeep         # Empty placeholder — keeps output/ in git
```

**Why is there an `output/` folder but no `input/` folder?**

Audio files are excluded by `.gitignore` and should stay wherever they naturally
live on your machine (`~/Downloads/`, `~/Recordings/`, etc.). You pass the full
path to whisperx at run time — no fixed input location is needed.

The `output/` folder is tracked (via `.gitkeep`) because R's `run_pipeline()`
writes to a known location that needs to exist on a fresh clone. Git does not
track empty folders, so `.gitkeep` is a conventional empty placeholder file that
ensures the folder is created when someone clones the repo.

After cloning, a colleague gets a ready-to-use `output/` folder with no extra
setup required.

---

## Acknowledgements

- [WhisperX](https://github.com/m-bain/whisperX) — Max Bain et al.
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) — Hervé Bredin et
  al.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — SYSTRAN
- [Ollama](https://ollama.com) — local LLM serving
- [Anthropic](https://anthropic.com) — Claude API
