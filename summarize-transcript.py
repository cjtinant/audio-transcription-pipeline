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
    "grant_planning": (
    "You are summarizing a grant planning meeting at a Tribal College. "
    "Given the following transcript with speaker labels and timestamps, provide:\n"
    "1. A 2-3 sentence overview of the grant or proposal under discussion\n"
    "2. Funding opportunities or mechanisms mentioned\n"
    "3. Key decisions made about approach, scope, or infrastructure\n"
    "4. Risks and open questions identified\n"
    "5. Action items with speaker attribution and any deadlines mentioned\n"
    "6. Next steps and timeline\n\n"
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


def read_txt_transcript(txt_path: str) -> str:
    """
    Read a human-cleaned plain-text transcript.

    Args:
        txt_path: Path to the cleaned .txt transcript file.

    Returns:
        Full transcript as a string, ready for LLM input.
    """
    path = Path(txt_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    return path.read_text(encoding="utf-8")


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
    input_path: str,
    output_dir: str = "output/processed",
) -> dict[str, str]:
    """
    Save summary to disk. Transcript copy is skipped when input is already
    a cleaned .txt — the input file is the transcript.

    Args:
        transcript:  Formatted transcript string
        summary:     LLM summary string
        input_path:  Input file path (used to derive output filenames)
        output_dir:  Directory to save outputs

    Returns:
        Dict with keys: transcript_path (None if input was .txt), summary_path
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    base = Path(input_path).stem
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("── Saved ───────────────────────────────────")

    # Skip transcript copy when input is already a cleaned .txt
    transcript_path = None
    if Path(input_path).suffix.lower() != ".txt":
        transcript_path = out / f"{base}_transcript_{ts}.txt"
        transcript_path.write_text(transcript, encoding="utf-8")
        print(f"Transcript: {transcript_path}")

    # Always save summary
    summary_path = out / f"{base}_summary_{ts}.txt"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Summary:    {summary_path}\n")

    return {
        "transcript_path": str(transcript_path) if transcript_path else None,
        "summary_path":    str(summary_path),
    }


# ── 6. Full pipeline ──────────────────────────────────────────────────

def run_pipeline(
    input_path: str,
    engine: str = "ollama",
    meeting_type: str = "general",
    custom_prompt: str | None = None,
    save: bool = True,
    output_dir: str = "output/processed",
    model: str | None = None,
) -> dict:
    """
    Run the full transcription and summarization pipeline.

    Args:
        input_path:    Path to input file — cleaned .txt (recommended) or
                       raw WhisperX .json (quick path, no human review)
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
        # Cleaned .txt — recommended path
        result = run_pipeline("output/processed/meeting_clean.txt",
                              engine="anthropic",
                              meeting_type="general")

        # Raw JSON — quick path, no human review
        result = run_pipeline("output/raw/meeting.json",
                              engine="anthropic",
                              meeting_type="general")

        # Custom prompt
        result = run_pipeline("output/processed/meeting_clean.txt",
                              meeting_type="custom",
                              custom_prompt="List every action item and who owns it.")
    """
    if engine not in ("ollama", "anthropic"):
        raise ValueError("engine must be 'ollama' or 'anthropic'")

    # Parse — .txt (cleaned) or .json (raw WhisperX)
    suffix = Path(input_path).suffix.lower()
    if suffix == ".txt":
        print("── Reading cleaned transcript (.txt) ───────")
        segments   = None
        transcript = read_txt_transcript(input_path)
    else:
        print("── Parsing transcript (.json) ──────────────")
        segments   = read_whisperx(input_path)
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
        paths = save_outputs(transcript, summary, input_path, output_dir)

    return {
        "segments":   segments,
        "transcript": transcript,
        "summary":    summary,
        "paths":      paths,
    }


# ── 7. Merge two summaries ────────────────────────────────────────────

def merge_summaries(
    summary1: str,
    summary2: str,
    engine: str,
    model: str | None = None,
    api_key: str | None = None,
    host: str = "http://127.0.0.1:11434",
) -> str:
    """
    Merge two independently generated summaries using an LLM.

    Args:
        summary1:  First summary string
        summary2:  Second summary string
        engine:    LLM backend — "ollama" or "anthropic"
        model:     Override model name
        api_key:   Anthropic API key (default: ANTHROPIC_API_KEY env var)
        host:      Ollama server URL

    Returns:
        Merged summary as a string
    """
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: uv pip install httpx")

    full_prompt = (
        "You are merging two independently generated summaries of the same meeting. "
        "Produce one comprehensive summary that includes all unique information from both. "
        "Do not duplicate content. Where the summaries differ on the same point, prefer "
        "the more specific or detailed version. Preserve all section headings.\n\n"
        f"Summary A:\n{summary1}\n\nSummary B:\n{summary2}"
    )

    if engine == "anthropic":
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set.")
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      model or "claude-sonnet-4-6",
                "max_tokens": 2048,
                "messages":   [{"role": "user", "content": full_prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    else:
        try:
            response = httpx.post(
                f"{host}/api/generate",
                json={
                    "model":  model or "llama3.1:8b-instruct-q6_k",
                    "prompt": full_prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Start it with: ollama serve")
        return response.json()["response"]


# ── 8. Merged pipeline ────────────────────────────────────────────────

def run_pipeline_merged(
    input_path: str,
    engine: str = "ollama",
    meeting_type: str = "general",
    custom_prompt: str | None = None,
    save: bool = True,
    output_dir: str = "output/processed",
    model: str | None = None,
) -> dict:
    """
    Run the pipeline twice and merge the results for a more complete summary.

    LLM outputs are non-deterministic: two runs of the same prompt will
    capture different details. This function runs the summarizer twice,
    then uses the LLM to merge both outputs into one comprehensive summary.

    Args:
        input_path:    Path to cleaned .txt (recommended) or raw .json
        engine:        LLM backend — "ollama" or "anthropic"
        meeting_type:  Prompt preset
        custom_prompt: Your own prompt (if meeting_type="custom")
        save:          Whether to save merged summary to disk
        output_dir:    Directory for saved outputs
        model:         Override model name

    Returns:
        Dict with keys: transcript, summary1, summary2, summary_merged, paths
    """
    if engine not in ("ollama", "anthropic"):
        raise ValueError("engine must be 'ollama' or 'anthropic'")

    # Parse
    suffix = Path(input_path).suffix.lower()
    if suffix == ".txt":
        print("── Reading cleaned transcript (.txt) ───────")
        segments   = None
        transcript = read_txt_transcript(input_path)
    else:
        print("── Parsing transcript (.json) ──────────────")
        segments   = read_whisperx(input_path)
        transcript = format_transcript(segments)

    prompt = get_prompt(meeting_type, custom_prompt)
    kwargs = {"model": model} if model else {}

    print("── Run 1 ───────────────────────────────────")
    if engine == "anthropic":
        summary1 = summarize_anthropic(transcript, prompt, **kwargs)
    else:
        summary1 = summarize_ollama(transcript, prompt, **kwargs)

    print("── Run 2 ───────────────────────────────────")
    if engine == "anthropic":
        summary2 = summarize_anthropic(transcript, prompt, **kwargs)
    else:
        summary2 = summarize_ollama(transcript, prompt, **kwargs)

    print("── Merging ─────────────────────────────────")
    summary_merged = merge_summaries(summary1, summary2, engine)
    print(summary_merged, "\n")

    paths = None
    if save:
        paths = save_outputs(transcript, summary_merged, input_path, output_dir)

    return {
        "segments":       segments,
        "transcript":     transcript,
        "summary1":       summary1,
        "summary2":       summary2,
        "summary_merged": summary_merged,
        "paths":          paths,
    }


# ── 9. CLI entry point ────────────────────────────────────────────────

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
        "input_path",
        nargs="?",
        help="Path to input file: cleaned .txt (recommended) or raw WhisperX .json",
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
        default="output/processed",
        help="Directory for saved outputs (default: output/processed)",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Run summarizer twice and merge results for a more complete summary",
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

    if not args.input_path:
        parser.print_help()
        sys.exit(1)

    fn = run_pipeline_merged if args.merge else run_pipeline
    fn(
        input_path    = args.input_path,
        engine        = args.engine,
        meeting_type  = args.meeting_type,
        custom_prompt = args.custom_prompt,
        save          = not args.no_save,
        output_dir    = args.output_dir,
        model         = args.model,
    )


if __name__ == "__main__":
    main()
