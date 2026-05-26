#!/usr/bin/env bash
# audio-transcription-pipeline/transcribe.sh
# ─────────────────────────────────────────────────────────────────────
# Bash/zsh wrapper for running WhisperX on any audio file.
#
# Installation:
#   mkdir -p ~/bin
#   cp transcribe.sh ~/bin/transcribe
#   chmod +x ~/bin/transcribe
#   # Ensure ~/bin is on your PATH (add to ~/.zshrc or ~/.bashrc):
#   #   export PATH="$HOME/bin:$PATH"
#
# Usage:
#   transcribe /full/path/to/meeting.m4a
#   transcribe /full/path/to/meeting.m4a --min_speakers 2 --max_speakers 2
#   transcribe /full/path/to/meeting.m4a --language fr
#
# Note: Always pass the full path to the audio file.
#       Zoom recordings live in ~/Documents/Zoom/ — wrap paths in quotes
#       if the folder name contains spaces.
# ─────────────────────────────────────────────────────────────────────

# Suppress harmless torchcodec warning
export PYTHONWARNINGS="ignore::UserWarning:pyannote"

# Activate the WhisperX virtual environment
source ~/audio-transcription-pipeline/.venv/bin/activate

# Load HF token from ~/.Renviron
hf_token=$(grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')

if [ -z "$hf_token" ]; then
    echo "Error: HF_TOKEN not found in ~/.Renviron"
    echo "Add it with: echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron"
    exit 1
fi

# Run WhisperX — full path avoids PATH issues after venv activation.
# All arguments passed to this script are forwarded to whisperx.
exec ~/audio-transcription-pipeline/.venv/bin/whisperx "$@" \
    --model large-v2 \
    --diarize \
    --hf_token "$hf_token" \
    --device cpu \
    --compute_type int8 \
    --output_format json \
    --output_dir ~/audio-transcription-pipeline/output \
    --language en
