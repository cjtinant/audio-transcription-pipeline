# Installation Guide

Platform-by-platform setup for the audio transcription pipeline. Choose your
platform and follow the steps in order.

---

## Security First

**Your API tokens must never appear in code or be committed to git.**

This repo's `.gitignore` is configured to exclude credential files, audio files,
and output files. Before doing anything else:

1. Never paste a token into any `.R`, `.py`, or `.sh` file
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

**Step 6 — Install the transcribe script**

```bash
mkdir -p ~/bin
cp transcribe.sh ~/bin/transcribe
chmod +x ~/bin/transcribe
```

Add `~/bin` to your PATH if it isn't already (add to `~/.zshrc` or `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
```

**Step 7 — Test it**

```bash
source .venv/bin/activate
curl -L "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" -o test.wav
.venv/bin/whisperx test.wav \
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

**Requirements:** macOS 13+, Homebrew at `/opt/homebrew`, uv

```bash
# Verify ARM Homebrew
file $(which brew)
# Expected: Bourne-Again shell script text executable

# Install tools
brew install uv ffmpeg git

# Create project venv with ARM-native Python 3.11
cd ~/audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate

# Install PyTorch and WhisperX
uv pip install torch torchaudio
uv pip install whisperx

# Verify ARM architecture
python3 -c "import torch; print(torch.__version__)"
file .venv/bin/python3
# Expected: Mach-O 64-bit executable arm64
```

**Device and compute settings:** `--device cpu --compute_type int8` is the
correct choice for Apple Silicon. WhisperX uses `faster-whisper` as its
transcription engine, which does not support Metal (MPS) natively. CPU with int8
quantization on Apple Silicon unified memory is both fast and reliable —
`large-v2` transcribes at approximately 10–15× realtime on M1 Max, meaning a
1-hour recording completes in 4–6 minutes. No alternative device flags are
needed or recommended.

**Install the transcribe script:**

```bash
mkdir -p ~/bin
cp transcribe.sh ~/bin/transcribe
chmod +x ~/bin/transcribe

# Make sure ~/bin is on your PATH — add to ~/.zshrc or ~/.bashrc:
#   export PATH="$HOME/bin:$PATH"

# Verify
transcribe --help   # should print WhisperX usage
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
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
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
source .venv/bin/activate
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

---

## Troubleshooting

**`whisperx: command not found` even after activating the venv** Use the full
path to the whisperx binary instead:

```bash
.venv/bin/whisperx your_audio.m4a ...
```

This happens because some terminals (Positron) don't always add the venv `bin/`
to PATH after activation. The full path always works.

**`whisperx: command not found`** The virtual environment is not activated.

```bash
source .venv/bin/activate
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

**Poor diarization (speakers mixed up or merged)** This is almost always fixed
by pinning the speaker count. Add `--min_speakers` and `--max_speakers` with the
exact number of speakers in your recording:

```bash
# 3-person meeting
transcribe meeting.m4a --min_speakers 3 --max_speakers 3

# 2-person interview
transcribe interview.m4a --min_speakers 2 --max_speakers 2
```

When auto-detection is left on (no flags), pyannote guesses the speaker count
from audio energy patterns — it works for 1–2 speakers but becomes unreliable
for 3+ speakers or when voices are similar. Pinning both values is low-effort
and high-impact. If you're unsure of the exact count, set a narrow range:
`--min_speakers 2 --max_speakers 4`.

**Slow transcription**

- Use a smaller model: `--model medium` or `--model base`
- Reduce batch size: `--batch_size 4`
- On Linux with NVIDIA GPU: use `--device cuda --compute_type float16`
