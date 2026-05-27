# Pipeline Reference

R and Python API reference, meeting type presets, and LLM backend options.

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
source .venv/bin/activate
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
