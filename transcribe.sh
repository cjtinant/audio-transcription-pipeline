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

# Suppress UserWarnings raised from pyannote modules. Known limitation:
# this does NOT catch the torchcodec/FFmpeg-8 startup warnings (they come
# from other modules with a different category) — those are cosmetic and
# tracked in WATERSHED.md, not suppressed here.
export PYTHONWARNINGS="ignore::UserWarning:pyannote"

# Locate the repo from this script's own path rather than assuming
# ~/PROJECTS/audio-transcription-pipeline — `make install` symlinks this file
# into ~/bin from wherever the repo was cloned, and installation.md tells
# users to clone wherever they like. Follow the symlink chain by hand:
# macOS's readlink has no dependable -f across the versions this repo targets.
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
    link_dir=$(cd -P "$(dirname "$src")" && pwd)
    src=$(readlink "$src")
    case "$src" in
        /*) ;;
        *) src="$link_dir/$src" ;;
    esac
done
repo_dir=$(cd -P "$(dirname "$src")" && pwd)

# Activate the WhisperX virtual environment
source "$repo_dir/.venv/bin/activate"

# Load the HF token. An exported HF_TOKEN wins — that is what installation.md
# tells WSL2 users to set, and nothing reads ~/.Renviron automatically there.
# Otherwise fall back to ~/.Renviron (the macOS/Linux path). The grep is
# anchored and capped at one match: an unanchored grep also matched
# commented-out lines and every duplicate the docs' `echo >>` pattern can
# append, and a second append would have produced a multi-line token.
hf_token="${HF_TOKEN:-}"
if [ -z "$hf_token" ] && [ -f "$HOME/.Renviron" ]; then
    hf_token=$(grep -m1 '^[[:space:]]*HF_TOKEN=' "$HOME/.Renviron" \
        | cut -d= -f2- | tr -d '\r')
fi

if [ -z "$hf_token" ]; then
    echo "Error: HF_TOKEN not set."
    echo "macOS/Linux: echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron"
    echo "WSL2:        echo 'export HF_TOKEN=hf_yourtoken' >> ~/.bashrc"
    exit 1
fi

# Output archive (see README "Where output goes"). Override the default
# location by exporting TRANSCRIBE_OUTPUT_DIR (the Python summarizer
# honors the same variable). A --output_dir passed on the command line
# still wins for whisperx's own output ("$@" comes last below), but the
# sidecar written here always follows the archive location.
output_dir="${TRANSCRIBE_OUTPUT_DIR:-$HOME/PROJECTS/audio-transcription-output}"
mkdir -p "$output_dir"

# Record the source audio path in a sidecar file, keyed by the output JSON's
# stem. The archive deliberately keeps audio out (private-archive design),
# but review-tooling (audio-linked spot-checking) needs a way to find the
# original file back. Written before `exec` below, since `exec` replaces
# this process and nothing after it would run.
audio_path=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
audio_stem=$(basename "$audio_path")
audio_stem="${audio_stem%.*}"
# Stem and path are passed as argv, NOT interpolated into the program
# text — an apostrophe in a path (e.g. Zoom's "...(he_they)'s Zoom
# Meeting" folder names) would break the quoting or worse.
python3 -c '
import json, sys
from pathlib import Path
sidecar = Path(sys.argv[3]) / ".source-audio.json"
data = {}
if sidecar.exists():
    try:
        data = json.loads(sidecar.read_text())
    except json.JSONDecodeError:
        data = {}
data[sys.argv[1]] = sys.argv[2]
sidecar.write_text(json.dumps(data, indent=2, sort_keys=True))
' "$audio_stem" "$audio_path" "$output_dir"

# Run WhisperX — full path avoids PATH issues after venv activation.
# All arguments passed to this script are forwarded to whisperx.
#
# "$@" comes LAST, after the hardcoded defaults, not before. argparse (which
# whisperx uses) takes the last occurrence when a flag repeats — with "$@"
# first, a user-supplied override (e.g. --model large-v2) was silently beaten
# by the hardcoded --model large-v3 coming after it. Defaults first, "$@"
# last means any hardcoded flag below can actually be overridden.
exec "$repo_dir/.venv/bin/whisperx" \
    --model large-v3 \
    --diarize \
    --hf_token "$hf_token" \
    --device cpu \
    --compute_type int8 \
    --output_format json \
    --output_dir "$output_dir" \
    --language en \
    "$@"
