# audio-transcription-pipeline/transcribe.fish
# ─────────────────────────────────────────────────────────────────────
# Fish shell function for running WhisperX on any audio file.
#
# Installation:
#   cp transcribe.fish ~/.config/fish/functions/transcribe.fish
#   source ~/.config/fish/config.fish
#
# Usage:
#   transcribe mymeeting.m4a
#   transcribe mymeeting.m4a --language en --min_speakers 2 --max_speakers 4
# ─────────────────────────────────────────────────────────────────────

function transcribe
    # Activate the WhisperX virtual environment
    source ~/audio-transcription-pipeline/.venv/bin/activate.fish

    # Load HF token from ~/.Renviron
    set hf_token (grep HF_TOKEN ~/.Renviron | cut -d= -f2 | tr -d '\r')

    if test -z "$hf_token"
        echo "Error: HF_TOKEN not found in ~/.Renviron"
        echo "Add it with: echo 'HF_TOKEN=hf_yourtoken' >> ~/.Renviron"
        return 1
    end

    # Run WhisperX with sensible defaults for Apple Silicon CPU
    whisperx $argv \
        --model large-v2 \
        --diarize \
        --hf_token "$hf_token" \
        --device cpu \
        --compute_type int8 \
        --output_format json \
        --output_dir ~/audio-transcription-pipeline/output \
        --language en
end
