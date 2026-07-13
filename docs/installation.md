# Installation Guide

Platform-by-platform setup for the audio transcription pipeline. Choose your
platform and follow the steps in order.

---

## Security First

**Your API tokens must never appear in code or be committed to git.**

This repo's `.gitignore` is configured to exclude credential files, audio files,
and output files. Before doing anything else:

1. Never paste a token into any `.py` or `.sh` file
2. Never commit `.Renviron` or `.env` files
3. Store all tokens in `~/.Renviron` — note that only `transcribe.sh` reads
   this automatically (via `grep`); the Python summarizer needs
   `ANTHROPIC_API_KEY` actually exported to your shell session (see
   Troubleshooting if you hit `ANTHROPIC_API_KEY not set`)
4. If you accidentally expose a token, invalidate it immediately at the
   provider's website and generate a new one

```bash
# Correct way to store tokens — in your home directory, not in the repo
echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron
echo 'ANTHROPIC_API_KEY=sk-ant-yourkey' >> ~/.Renviron
```

---

## Private Output Archive Setup

One-time setup, done once per machine, before first use.

This pipeline never stores research transcripts inside its own repo folder.
All output — raw JSON, cleaned transcripts, summaries, reviewed HTML — is
written directly to a separate, private folder outside the repo:

```bash
mkdir -p ~/PROJECTS/audio-transcription-output
cd ~/PROJECTS/audio-transcription-output
git init
echo ".DS_Store" > .gitignore
git add .gitignore
git commit -m "chore: initial commit, ignore .DS_Store"
```

**Local git only — no remote.** This gives version history (recover a file
after a bad edit, an accidental deletion, or a script bug) without the data
ever leaving your machine. It is not a substitute for disk-level backup — if
the drive fails, git history fails with it. If you want protection against
that too, back this folder up separately (Time Machine, an external drive,
etc.).

**Why a separate folder instead of `output/` inside this repo:** this repo
is public. A sibling folder outside the repo entirely means transcripts can
never end up in git history here, even by accident — a stronger guarantee
than relying on `.gitignore` alone. Full design reasoning is in
[WATERSHED.md](../WATERSHED.md).

---

## Exact Versions (Reproducibility)

The install steps below deliberately pin only the direct dependencies
(torch/torchaudio, whisperx, httpx) and let the resolver pick the rest. The
exact versions this pipeline was built and tested against are snapshotted in
[`requirements-lock.txt`](../requirements-lock.txt) (recorded 2026-07-12,
macOS arm64, Python 3.11). Check it first when debugging version-specific
behavior — the torchcodec warnings and the pyannote model-default claims in
this repo were all verified against those versions. To reproduce the tested
environment exactly:

```bash
uv pip install -r requirements-lock.txt
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
git clone https://github.com/cjtinant/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio
uv pip install whisperx
uv pip install httpx
```

**Step 4 — Set up HuggingFace** (see [HuggingFace Setup](#huggingface-setup))

**Step 5 — Install the transcribe script**

```bash
make install
```

Add `~/bin` to your PATH if it isn't already (add to `~/.zshrc` or `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
```

**Step 6 — Test it**

```bash
source .venv/bin/activate
curl -L "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" -o test.wav
.venv/bin/whisperx test.wav \
  --model large-v3 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/PROJECTS/audio-transcription-output \
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
sudo apt update && sudo apt install -y git ffmpeg python3-pip curl build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

**Step 4 — Clone repo and set up environment**

```bash
git clone https://github.com/cjtinant/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
uv pip install httpx
```

**Step 5 — Set up HuggingFace** (see [HuggingFace Setup](#huggingface-setup))

**Step 6 — Install the transcribe script**

```bash
make install
```

Add `~/bin` to your PATH if it isn't already (add to `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
```

---

### Linux (Simple)

> Tested on Ubuntu 22.04+. Other distributions follow the same pattern.

```bash
# Install system dependencies
sudo apt update && sudo apt install -y git ffmpeg python3-pip curl build-essential

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and set up
git clone https://github.com/cjtinant/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
uv pip install httpx
```

**Install the transcribe script:**

```bash
make install
```

Add `~/bin` to your PATH if it isn't already (add to `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
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
cd ~/PROJECTS/audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate

# Install PyTorch and WhisperX
uv pip install torch torchaudio
uv pip install whisperx
uv pip install httpx

# Verify ARM architecture
python3 -c "import torch; print(torch.__version__)"
file .venv/bin/python3
# Expected: Mach-O 64-bit executable arm64
```

**Device and compute settings:** `--device cpu --compute_type int8` is the
correct choice for Apple Silicon. WhisperX uses `faster-whisper` as its
transcription engine, which does not support Metal (MPS) natively. CPU with int8
quantization on Apple Silicon unified memory is both fast and reliable —
`large-v2` transcribed at approximately 10–15× realtime on M1 Max, meaning a
1-hour recording completed in 4–6 minutes. This repo now defaults to
`large-v3` (see WATERSHED.md for the comparison); its speed on the same
hardware hasn't been separately measured yet — timing above is `large-v2`'s
figure, not verified for `large-v3`. No alternative device flags are needed
or recommended.

**Install the transcribe script:**

```bash
make install

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
- Performance: ~3-5x slower than Apple Silicon (figure measured for
  `large-v2`; not separately verified for `large-v3`, this repo's current
  default)

```bash
# Verify Homebrew location
which brew  # should be /usr/local/bin/brew
brew install uv ffmpeg git

cd ~/PROJECTS/audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install torch torchaudio
uv pip install whisperx
uv pip install httpx
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
git clone https://github.com/cjtinant/audio-transcription-pipeline.git
cd audio-transcription-pipeline

# Venv
uv venv --python 3.11 .venv
source .venv/bin/activate

# PyTorch CPU (default for WSL2 without NVIDIA GPU)
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
uv pip install httpx
```

**Install the transcribe script:**

```bash
make install
```

Add `~/bin` to your PATH if it isn't already (add to `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
```

**Audio files on Windows:** Your Windows files are accessible at
`/mnt/c/Users/YourName/`. Copy audio files to your WSL2 home first:

```bash
cp /mnt/c/Users/YourName/Downloads/meeting.m4a ~/audio-transcription-pipeline/
```

**Tokens in WSL2:** Add to `~/.bashrc` (nothing in this pipeline reads
`~/.Renviron` automatically on WSL2 — export tokens as shell env vars
instead):

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
sudo dnf install -y git ffmpeg python3-pip curl gcc make

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and set up
git clone https://github.com/cjtinant/audio-transcription-pipeline.git
cd audio-transcription-pipeline
uv venv --python 3.11 .venv
source .venv/bin/activate

# CPU only
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install whisperx
uv pip install httpx

# NVIDIA GPU (CUDA 12.4)
# uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
# Use: --device cuda --compute_type float16
```

**Install the transcribe script:**

```bash
make install
```

Add `~/bin` to your PATH if it isn't already (add to `~/.bashrc`):

```bash
export PATH="$HOME/bin:$PATH"
```

---

## HuggingFace Setup

WhisperX uses pyannote models for speaker diarization. These are gated (require
a free account and license agreement).

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Go to **Settings → Access Tokens → New token**
3. Select the **Read** tab, name it `whisperx-local`, click **Create**
4. Copy the `hf_...` token — you only see it once
5. Accept the license on the model page (must be logged in):
   - [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

   This is the only gated model this pipeline actually uses —
   `community-1` is WhisperX's hardcoded diarization default (confirmed in
   its source, `whisperx/diarize.py`) and is self-contained, not built on
   `speaker-diarization-3.1` or `segmentation-3.0`. See WATERSHED.md for how
   this was confirmed.
6. Add the token to your credentials file:

**macOS/Linux:**

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
cd ~/PROJECTS/audio-transcription-pipeline
curl -L "https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav" \
  -o test.wav
```

### Step 2 — Activate the environment and transcribe

```bash
source .venv/bin/activate
```

```bash
whisperx test.wav \
  --model large-v3 \
  --diarize \
  --hf_token "YOUR_HF_TOKEN" \
  --device cpu \
  --compute_type int8 \
  --output_format json \
  --output_dir ~/PROJECTS/audio-transcription-output \
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

Output file: `~/PROJECTS/audio-transcription-output/test.json`

### Step 3 — Verify summarization

```bash
python3 summarize-transcript.py \
  ~/PROJECTS/audio-transcription-output/test.json \
  --no-save   # skip saving for this test run
```

Uses Anthropic (default) — add `--engine ollama` instead if you're testing
the local/private path (needs `ollama serve` running).

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
rm test.wav ~/PROJECTS/audio-transcription-output/test.json
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

**`GatedRepoError: 403`** You haven't accepted the pyannote model license, or
your HF token is wrong.

- Visit the model page and click Agree (must be logged in) — see
  [HuggingFace Setup](#huggingface-setup); `speaker-diarization-community-1`
  is the only gated model this pipeline uses
- Verify your token: `grep HF_TOKEN ~/.Renviron`

**`ANTHROPIC_API_KEY not set`** Nothing in the Python path reads `~/.Renviron`
automatically — only `transcribe.sh` does (via `grep`, for `HF_TOKEN`). Export
it into your shell session for this terminal:

```bash
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY ~/.Renviron | cut -d= -f2 | tr -d '\r')
```

Add the same line to `~/.zshrc`/`~/.bashrc` if you don't want to repeat this
every new terminal session.

**`ModuleNotFoundError: No module named 'httpx'` or `Cannot find module httpx`**
`httpx` is missing from the venv. This venv is managed by `uv` — `pip install`
and `python3 -m pip install` will not work here. Run:

```bash
cd ~/PROJECTS/audio-transcription-pipeline
uv pip install httpx
```

Restart your terminal or IDE after installing.

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

When auto-detection is left on (no flags), pyannote estimates the speaker
count itself, by clustering speaker embeddings. In this pipeline's own
recordings it has been reliable for 1–2 speakers and less so for 3+ or
similar voices — anecdotal, from limited use, not benchmarked. Pinning both
values is low-effort and high-impact. If you're unsure of the exact count, set a narrow range:
`--min_speakers 2 --max_speakers 4`.

**Slow transcription**

- Use a smaller model: `--model medium` or `--model base`
- Reduce batch size: `--batch_size 4`
- On Linux with NVIDIA GPU: use `--device cuda --compute_type float16`
