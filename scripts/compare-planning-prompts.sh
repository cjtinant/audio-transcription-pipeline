#!/usr/bin/env bash
# Run the v2 prompt sequentially against three local Ollama models.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -ne 1 || ! -f "$1" ]]; then
    echo "Usage: bash scripts/compare-planning-prompts.sh /absolute/path/to/transcript.txt" >&2
    exit 1
fi
archive_dir="${TRANSCRIBE_OUTPUT_DIR:-$HOME/PROJECTS/audio-transcription-output}"
mkdir -p "$archive_dir"
run_dir="$(mktemp -d "$archive_dir/planning-v2.XXXXXX")"
cp "$1" "$run_dir/input.txt"
cp "$repo_dir/prompts/planning-reflection-v2.txt" "$run_dir/prompt.txt"
ollama list > "$run_dir/ollama-list.txt"
shasum -a 256 "$run_dir/input.txt" "$run_dir/prompt.txt" > "$run_dir/checksums.txt"
prompt_text="$(cat "$run_dir/prompt.txt")"
echo "Results: $run_dir"
for model in qwen3.6:35b granite4.1:30b nemotron3:33b; do
    model_dir="$run_dir/${model%%:*}"
    mkdir -p "$model_dir"
    printf 'model=%s\nengine=ollama\ntype=custom\nmerge=false\n' "$model" > "$model_dir/run-settings.txt"
    date -u '+started=%Y-%m-%dT%H:%M:%SZ' >> "$model_dir/run-settings.txt"
    if "$repo_dir/.venv/bin/python" "$repo_dir/summarize_transcript.py" \
        "$run_dir/input.txt" --engine ollama --model "$model" \
        --type custom --prompt "$prompt_text" --output-dir "$model_dir" \
        > "$model_dir/run.log" 2>&1; then
        date -u '+finished=%Y-%m-%dT%H:%M:%SZ' >> "$model_dir/run-settings.txt"
        echo "Completed: $model"
    else
        echo "Failed: $model; inspect $model_dir/run.log" >&2
        exit 1
    fi
done
echo "Compare the summaries in: $run_dir"
