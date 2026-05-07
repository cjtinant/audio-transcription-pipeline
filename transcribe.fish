# audio-transcription-pipeline/transcribe.fish
# ─────────────────────────────────────────────────────────────────────
# Fish shell function for running WhisperX on any audio file.
#
# Installation:
#   cp transcribe.fish ~/.config/fish/functions/transcribe.fish
#   source ~/.config/fish/config.fish
#
# Usage:
#   transcribe /full/path/to/meeting.m4a
#   transcribe /full/path/to/meeting.m4a --language en --min_speakers 2 --max_speakers 4
#
# Note: Always pass the full path to the audio file.
#       Zoom recordings live in ~/Documents/Zoom/ — wrap paths in quotes
#       if the folder name contains spaces or parentheses.
# ─────────────────────────────────────────────────────────────────────

function transcribe
    # Suppress harmless torchcodec warning
    set -x PYTHONWARNINGS "ignore::UserWarning:pyannote"

    # Activate the WhisperX virtual environment
    source ~/audio-transcription-pipeline/.venv/bin/activate.fish

    # Load HF token from ~/.Renviron
    set hf_token (grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')

    if test -z "$hf_token"
        echo "Error: HF_TOKEN not found in ~/.Renviron"
        echo "Add it with: echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron"
        return 1
    end

    # Run WhisperX using full path to avoid PATH issues in fish
    ~/audio-transcription-pipeline/.venv/bin/whisperx $argv \
        --model large-v2 \
        --diarize \
        --hf_token "$hf_token" \
        --device cpu \
        --compute_type int8 \
        --output_format json \
        --output_dir ~/audio-transcription-pipeline/output \
        --language en
end
