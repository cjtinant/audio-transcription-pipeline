#!/usr/bin/env bash
# audio-transcription-pipeline/transcribe.sh
# ─────────────────────────────────────────────────────────────────────
# Bash/zsh wrapper for running WhisperX on any audio file.
#
# Installation:
#   make install
#   # Ensure ~/bin is on your PATH (add to ~/.zshrc or ~/.bashrc):
#   #   export PATH="$HOME/bin:$PATH"
#
# Usage:
#   transcribe /full/path/to/meeting.m4a
#   transcribe /full/path/to/meeting.m4a --min_speakers 2 --max_speakers 3
#   transcribe /full/path/to/meeting.m4a --language en
#
# Note: Always pass the full path to the audio file.
#       Zoom recordings live in ~/Zoom/ — wrap paths in quotes
#       if the folder name contains spaces.
# ─────────────────────────────────────────────────────────────────────

# Suppress harmless torchcodec warning
export PYTHONWARNINGS="ignore::UserWarning:pyannote"

# Activate the WhisperX virtual environment
source ~/PROJECTS/audio-transcription-pipeline/.venv/bin/activate

# Load HF token from ~/.Renviron
hf_token=$(grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')

if [ -z "$hf_token" ]; then
    echo "Error: HF_TOKEN not found in ~/.Renviron"
    echo "Add it with: echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron"
    exit 1
fi

# Record the source audio path in a sidecar file, keyed by the output JSON's
# stem. The archive deliberately keeps audio out (private-archive design),
# but review-tooling (audio-linked spot-checking) needs a way to find the
# original file back. Written before `exec` below, since `exec` replaces
# this process and nothing after it would run.
audio_path=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
audio_stem=$(basename "$audio_path")
audio_stem="${audio_stem%.*}"
python3 -c "
import json
from pathlib import Path
sidecar = Path.home() / 'PROJECTS/audio-transcription-output/.source-audio.json'
data = {}
if sidecar.exists():
    try:
        data = json.loads(sidecar.read_text())
    except json.JSONDecodeError:
        data = {}
data['$audio_stem'] = '$audio_path'
sidecar.write_text(json.dumps(data, indent=2, sort_keys=True))
"

# Run WhisperX — full path avoids PATH issues after venv activation.
# All arguments passed to this script are forwarded to whisperx.
#
# "$@" comes LAST, after the hardcoded defaults, not before. argparse (which
# whisperx uses) takes the last occurrence when a flag repeats — with "$@"
# first, a user-supplied override (e.g. --model large-v2) was silently beaten
# by the hardcoded --model large-v3 coming after it. Defaults first, "$@"
# last means any hardcoded flag below can actually be overridden.
exec ~/PROJECTS/audio-transcription-pipeline/.venv/bin/whisperx \
    --model large-v3 \
    --diarize \
    --hf_token "$hf_token" \
    --device cpu \
    --compute_type int8 \
    --output_format json \
    --output_dir ~/PROJECTS/audio-transcription-output \
    --language en \
    "$@"
