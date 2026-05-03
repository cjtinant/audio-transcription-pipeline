#!/usr/bin/env python3
"""
audio-transcription-pipeline/transcribe.py
─────────────────────────────────────────────────────────────────────
Full pipeline: WhisperX JSON → formatted transcript → LLM summary

Interactive usage (Python REPL or script):
    from transcribe import run_pipeline
    result = run_pipeline("output/meeting.json")
    result = run_pipeline("output/meeting.json",
                          engine="anthropic",
                          meeting_type="interview")

CLI usage:
    python transcribe.py output/meeting.json
    python transcribe.py output/meeting.json --engine anthropic
    python transcribe.py output/meeting.json --type interview
    python transcribe.py output/meeting.json --type custom \
        --prompt "Summarize this grant meeting, focusing on deadlines."
    python transcribe.py output/meeting.json --no-save
    python transcribe.py output/meeting.json --list-types
─────────────────────────────────────────────────────────────────────
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── 1. Meeting type prompt presets ────────────────────────────────────

MEETING_PROMPTS = {
    "general": (
        "You are a professional meeting summarizer. "
        "Given the following transcript with speaker labels and timestamps, provide:\n"
        "1. A 2-3 sentence overview of the meeting\n"
        "2. Key decisions made\n"
        "3. Action items with speaker attribution\n"
        "4. Any open questions or unresolved issues\n\n"
    ),
    "standup": (
        "You are summarizing a standup meeting. "
        "Given the following transcript with speaker labels and timestamps, provide:\n"
        "1. What each speaker reported they completed\n"
        "2. What each speaker is working on today\n"
        "3. Any blockers or impediments raised\n\n"
    ),
    "interview": (
        "You are summarizing a research interview or conversation. "
        "Given the following transcript with speaker labels and timestamps, provide:\n"
        "1. A 2-3 sentence overview of the conversation topic\n"
        "2. Key themes and insights from the interviewee\n"
        "3. Notable quotes or moments (with timestamps)\n"
        "4. Follow-up questions worth exploring\n\n"
    ),
    "research": (
        "You are summarizing a research discussion. "
        "Given the following transcript with speaker labels and timestamps, provide:\n"
        "1. Research question or topic under discussion\n"
        "2. Key findings or arguments raised\n"
        "3. Methodological points discussed\n"
        "4. Next steps or gaps identified\n\n"
    ),
    "lecture": (
        "You are summarizing a lecture or presentation. "
        "Given the following transcript with speaker labels and timestamps, provide:\n"
        "1. Main topic and learning objectives\n"
        "2. Key concepts covered (with timestamps)\n"
        "3. Examples or case studies mentioned\n"
        "4. Summary suitable for study notes\n\n"
    ),
}

MEETING_TYPE_DESCRIPTIONS = {
    "general":   "Team meetings, calls — overview, decisions, action items, open questions",
    "standup":   "Daily standups — completed work, today's plan, blockers per speaker",
    "interview": "Research/user interviews — themes, insights, notable quotes, follow-ups",
    "research":  "Academic discussions — research question, findings, methods, next steps",
    "lecture":   "Lectures/presentations — topics, key concepts with timestamps, study notes",
    "custom":    "Provide your own prompt via --prompt or custom_prompt argument",
}


def get_prompt(meeting_type: str, custom_prompt: str | None = None) -> str:
    """Return the summarization prompt for a given meeting type."""
    if meeting_type == "custom":
        if not custom_prompt:
            raise ValueError(
                "Provide a custom_prompt string when meeting_type='custom'"
            )
        return custom_prompt
    if meeting_type not in MEETING_PROMPTS:
        raise ValueError(
            f"Unknown meeting_type '{meeting_type}'. "
            f"Choose from: {', '.join(MEETING_PROMPTS)} or 'custom'"
        )
    return MEETING_PROMPTS[meeting_type]


# ── 2. Parse WhisperX JSON output ─────────────────────────────────────

def read_whisperx(json_path: str) -> list[dict]:
    """
    Read a WhisperX JSON output file.

    Args:
        json_path: Path to the WhisperX JSON output file.

    Returns:
        List of segment dicts with keys: start, end, speaker, text
    """
    path = Path(json_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    segments = []
    for seg in data.get("segments", []):
        segments.append({
            "start":   seg.get("start", 0.0),
            "end":     seg.get("end", 0.0),
            "speaker": seg.get("speaker", "UNKNOWN"),
            "text":    seg.get("text", "").strip(),
        })
    return segments


# ── 3. Format segments for LLM input ──────────────────────────────────

def format_transcript(segments: list[dict]) -> str:
    """
    Format a list of segments into a readable transcript string.

    Args:
        segments: List of segment dicts from read_whisperx()

    Returns:
        Formatted transcript string for LLM input
    """
    lines = []
    for seg in segments:
        lines.append(
            f"[{seg['speaker']} @ {seg['start']:.1f}s] {seg['text']}"
        )
    return "\n".join(lines)


# ── 4. LLM backends ───────────────────────────────────────────────────

def summarize_anthropic(
    transcript: str,
    prompt: str,
    model: str = "claude-sonnet-4-6",
    api_key: str | None = None,
) -> str:
    """
    Summarize a transcript using the Anthropic API.

    Args:
        transcript: Formatted transcript string
        prompt:     System prompt from get_prompt()
        model:      Anthropic model ID (default: claude-sonnet-4-6)
        api_key:    Anthropic API key (default: ANTHROPIC_API_KEY env var)

    Returns:
        Summary as a string
    """
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: uv pip install httpx")

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set.\n"
            "Add it to ~/.Renviron (R) or ~/.bashrc / ~/.zshrc (shell):\n"
            "  export ANTHROPIC_API_KEY=sk-ant-yourkey"
        )

    full_prompt = prompt + "Transcript:\n" + transcript

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      model,
            "max_tokens": 1024,
            "messages":   [{"role": "user", "content": full_prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def summarize_ollama(
    transcript: str,
    prompt: str,
    model: str = "llama3.1:8b-instruct-q6_k",
    host: str = "http://127.0.0.1:11434",
) -> str:
    """
    Summarize a transcript using a local Ollama model.

    Args:
        transcript: Formatted transcript string
        prompt:     System prompt from get_prompt()
        model:      Ollama model name
        host:       Ollama server URL (default: http://127.0.0.1:11434)

    Returns:
        Summary as a string
    """
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: uv pip install httpx")

    full_prompt = prompt + "Transcript:\n" + transcript

    try:
        response = httpx.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": full_prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
    except httpx.ConnectError:
        raise ConnectionError(
            "Cannot connect to Ollama. Start it with: ollama serve"
        )

    return response.json()["response"]


# ── 5. Save outputs ───────────────────────────────────────────────────

def save_outputs(
    transcript: str,
    summary: str,
    json_path: str,
    output_dir: str = "output",
) -> dict[str, str]:
    """
    Save transcript and summary to disk with timestamped filenames.

    Args:
        transcript:  Formatted transcript string
        summary:     LLM summary string
        json_path:   Original JSON path (used to derive output filenames)
        output_dir:  Directory to save outputs

    Returns:
        Dict with keys: transcript_path, summary_path
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    base = Path(json_path).stem
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")

    transcript_path = out / f"{base}_transcript_{ts}.txt"
    summary_path    = out / f"{base}_summary_{ts}.txt"

    transcript_path.write_text(transcript, encoding="utf-8")
    summary_path.write_text(summary, encoding="utf-8")

    print("── Saved ───────────────────────────────────")
    print(f"Transcript: {transcript_path}")
    print(f"Summary:    {summary_path}\n")

    return {
        "transcript_path": str(transcript_path),
        "summary_path":    str(summary_path),
    }


# ── 6. Full pipeline ──────────────────────────────────────────────────

def run_pipeline(
    json_path: str,
    engine: str = "ollama",
    meeting_type: str = "general",
    custom_prompt: str | None = None,
    save: bool = True,
    output_dir: str = "output",
    model: str | None = None,
) -> dict:
    """
    Run the full transcription and summarization pipeline.

    Args:
        json_path:     Path to WhisperX JSON output file
        engine:        LLM backend — "ollama" (local/free) or "anthropic"
        meeting_type:  Prompt preset — "general", "standup", "interview",
                       "research", "lecture", or "custom"
        custom_prompt: Your own prompt string (if meeting_type="custom")
        save:          Whether to save transcript and summary to disk
        output_dir:    Directory for saved outputs
        model:         Override the default LLM model name

    Returns:
        Dict with keys: segments, transcript, summary, paths (if saved)

    Examples:
        # Local Ollama, general meeting (default)
        result = run_pipeline("output/meeting.json")

        # Anthropic API, interview preset
        result = run_pipeline("output/interview.json",
                              engine="anthropic",
                              meeting_type="interview")

        # Custom prompt, local Ollama
        result = run_pipeline("output/meeting.json",
                              meeting_type="custom",
                              custom_prompt="List every number mentioned.")

        # Override model
        result = run_pipeline("output/meeting.json",
                              model="llama3.1:8b-instruct-q8_0")
    """
    if engine not in ("ollama", "anthropic"):
        raise ValueError("engine must be 'ollama' or 'anthropic'")

    # Parse
    print("── Parsing transcript ──────────────────────")
    segments   = read_whisperx(json_path)
    transcript = format_transcript(segments)

    print("── Transcript ──────────────────────────────")
    print(transcript, "\n")

    # Build prompt
    prompt = get_prompt(meeting_type, custom_prompt)

    # Summarize
    print(f"── Summarizing via {engine} ({meeting_type}) ──")
    if engine == "anthropic":
        kwargs = {"model": model} if model else {}
        summary = summarize_anthropic(transcript, prompt, **kwargs)
    else:
        kwargs = {"model": model} if model else {}
        summary = summarize_ollama(transcript, prompt, **kwargs)

    print(summary, "\n")

    # Save
    paths = None
    if save:
        paths = save_outputs(transcript, summary, json_path, output_dir)

    return {
        "segments":   segments,
        "transcript": transcript,
        "summary":    summary,
        "paths":      paths,
    }


# ── 7. CLI entry point ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Summarize a WhisperX transcript using a local or cloud LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python transcribe.py output/meeting.json
  python transcribe.py output/meeting.json --engine anthropic
  python transcribe.py output/meeting.json --type interview
  python transcribe.py output/meeting.json --type custom \\
      --prompt "List every action item and who owns it."
  python transcribe.py output/meeting.json --model llama3.1:8b-instruct-q8_0
  python transcribe.py --list-types
        """,
    )

    parser.add_argument(
        "json_path",
        nargs="?",
        help="Path to WhisperX JSON output file",
    )
    parser.add_argument(
        "--engine",
        choices=["ollama", "anthropic"],
        default="ollama",
        help="LLM backend (default: ollama)",
    )
    parser.add_argument(
        "--type",
        dest="meeting_type",
        choices=list(MEETING_PROMPTS.keys()) + ["custom"],
        default="general",
        help="Meeting type preset (default: general)",
    )
    parser.add_argument(
        "--prompt",
        dest="custom_prompt",
        default=None,
        help="Custom prompt string (required if --type custom)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Override LLM model name. "
            "Ollama default: llama3.1:8b-instruct-q6_k  "
            "Anthropic default: claude-sonnet-4-6"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for saved outputs (default: output)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save transcript and summary to disk",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available meeting types and exit",
    )

    args = parser.parse_args()

    # --list-types
    if args.list_types:
        print("\nAvailable meeting types:\n")
        for name, desc in MEETING_TYPE_DESCRIPTIONS.items():
            print(f"  {name:<12} {desc}")
        print()
        sys.exit(0)

    if not args.json_path:
        parser.print_help()
        sys.exit(1)

    run_pipeline(
        json_path     = args.json_path,
        engine        = args.engine,
        meeting_type  = args.meeting_type,
        custom_prompt = args.custom_prompt,
        save          = not args.no_save,
        output_dir    = args.output_dir,
        model         = args.model,
    )


if __name__ == "__main__":
    main()
