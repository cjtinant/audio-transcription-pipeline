#!/usr/bin/env python3
"""
sanity_check_transcript.py
---------------------------
LLM plausibility pass over a transcript: flags words/phrases that read as
semantically odd or out of place — a different error category than
acoustic confidence (review_transcript.py --report) or cross-model
disagreement (compare_transcripts.py). Catches cases where a single model
is confident and wrong in a way that doesn't disagree with anything else,
it just doesn't make sense in context.

Usage:
    python3 sanity_check_transcript.py transcript.json
    python3 sanity_check_transcript.py transcript.json --engine ollama
    python3 sanity_check_transcript.py transcript.json --known-terms my-terms.txt
    python3 sanity_check_transcript.py transcript.json --out report.txt

Defaults to Anthropic (Claude) — a real test against this transcript
(2026-07-12, logged in WATERSHED) found it noticeably more reliable than
Ollama's local llama3.1 model for this task: it quoted flagged phrases
verbatim every time (Ollama missed once), and its flags lined up with
real trouble spots compare_transcripts.py had independently found. Ollama
remains fully supported via --engine ollama for local/private processing —
use it for sensitive recordings you don't want sent to Anthropic's servers.

Combined with a known-terms list (institution-specific vocabulary, proper
nouns, technical terms) supplied to the model as context, so it doesn't
flag legitimate but unusual words as errors — the same false-positive risk
already identified for a plain spell-check pass. Treated as one combined
"sanity pass" feature rather than two separate builds, per the original
scoping note in WATERSHED.

Reuses summarize_transcript.py's summarize_anthropic/summarize_ollama for
the actual LLM call and review_transcript.py's load_segments for parsing
WhisperX JSON and locating flagged phrases back to a timestamp.

Flags are a signal, not a fix — same as --report and compare_transcripts.py,
still requires human judgment to resolve.
"""

import argparse
import re
import sys
from pathlib import Path

from review_transcript import load_segments
from summarize_transcript import summarize_anthropic, summarize_ollama


DEFAULT_KNOWN_TERMS_FILE = Path(__file__).parent / "known-terms.txt"

# NOTE: no {transcript} placeholder here — summarize_anthropic/
# summarize_ollama already do `prompt + "Transcript:\n" + transcript`
# internally, matching how the rest of the pipeline builds prompts.
SANITY_CHECK_PROMPT = """You are reviewing a meeting transcript for likely mistranscriptions — words or phrases that seem semantically odd, contradictory, or out of place given the surrounding context. This transcript was produced automatically by a speech-to-text model and may contain errors.

Known vocabulary specific to this context — do NOT flag these as errors even if they seem unusual, and do not flag informal speech, filler words, or casual grammar:
{known_terms}

For each phrase that seems like a likely mistranscription, respond in exactly this format, one block per flag, nothing else around it:

FLAG: <exact phrase from the transcript, copied verbatim>
REASON: <one sentence on why this seems like a mistranscription>

If you find nothing worth flagging, respond with exactly: NONE FOUND

"""


def load_known_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def format_transcript_for_llm(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        text = " ".join(w["w"] for w in seg.get("words", []))
        m, s = divmod(int(seg.get("start", 0)), 60)
        lines.append(f"[{seg.get('speaker', 'UNKNOWN')} @ {m}:{s:02d}] {text}")
    return "\n".join(lines)


def parse_flags(response: str) -> list[dict]:
    """Parse the LLM's FLAG:/REASON: blocks into a list of dicts."""
    if response.strip().upper().startswith("NONE FOUND"):
        return []
    flags = []
    chunks = re.split(r"\bFLAG:\s*", response)
    for chunk in chunks[1:]:  # chunks[0] is any preamble before the first FLAG
        parts = chunk.split("REASON:", 1)
        phrase = parts[0].strip()
        reason = ""
        if len(parts) > 1:
            # Cut at the next line break so a run-on response doesn't bleed
            # into the following FLAG block.
            reason = parts[1].strip().splitlines()[0].strip() if parts[1].strip() else ""
        if phrase:
            flags.append({"phrase": phrase, "reason": reason})
    return flags


def normalize(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def locate_phrase(phrase: str, flat_words: list[dict]) -> float | None:
    """
    Find where a flagged phrase occurs in the flattened word list and
    return its start timestamp. Matches on normalized word sequences —
    tolerant of minor punctuation/casing differences between the LLM's
    quoted phrase and the original transcript text.
    """
    phrase_words = [normalize(w) for w in phrase.split() if normalize(w)]
    if not phrase_words:
        return None
    norm_words = [normalize(w["w"]) for w in flat_words]
    n = len(phrase_words)
    for i in range(len(norm_words) - n + 1):
        if norm_words[i:i + n] == phrase_words:
            return flat_words[i]["t"]
    return None


def fmt_time(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def flatten_words(segments: list[dict]) -> list[dict]:
    flat = []
    for seg in segments:
        for w in seg.get("words", []):
            flat.append({
                "w": w["w"],
                "t": w["t"] if w.get("t") is not None else seg.get("start", 0),
            })
    return flat


def build_sanity_report(flags: list[dict], flat_words: list[dict]) -> str:
    if not flags:
        return "0 flag(s) — nothing found by the sanity pass\n" + "=" * 40

    lines = []
    unlocated = 0
    for flag in flags:
        ts = locate_phrase(flag["phrase"], flat_words)
        if ts is not None:
            ts_str = fmt_time(ts)
        else:
            ts_str = "?:??"
            unlocated += 1
        lines.append(
            f"[{ts_str}] {flag['phrase']!r}\n"
            f"    {flag['reason']}"
        )

    header = f"{len(flags)} flag(s) from the sanity pass"
    if unlocated:
        header += f" ({unlocated} could not be matched back to a timestamp)"
    header += "\n" + "=" * len(header)
    return header + "\n\n" + "\n\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="LLM plausibility pass over a transcript — flags likely mistranscriptions."
    )
    parser.add_argument("json_path", help="Path to WhisperX JSON transcript")
    parser.add_argument(
        "--engine", choices=["ollama", "anthropic"], default="anthropic",
        help="LLM backend (default: anthropic; use ollama for local/private processing)"
    )
    parser.add_argument("--model", default=None, help="Override the default LLM model name")
    parser.add_argument(
        "--known-terms", default=None,
        help=(
            f"Path to a known-terms file, one term per line, '#' comments "
            f"allowed (default: {DEFAULT_KNOWN_TERMS_FILE.name} next to this script)"
        )
    )
    parser.add_argument(
        "--out", default=None,
        help="Write report to this path (default: print to stdout)"
    )
    args = parser.parse_args()

    json_path = Path(args.json_path).expanduser().resolve()
    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    known_terms_path = (
        Path(args.known_terms).expanduser().resolve()
        if args.known_terms else DEFAULT_KNOWN_TERMS_FILE
    )
    known_terms = load_known_terms(known_terms_path)
    known_terms_str = "\n".join(f"- {t}" for t in known_terms) if known_terms else "(none provided)"

    segments = load_segments(json_path)
    flat_words = flatten_words(segments)
    transcript_text = format_transcript_for_llm(segments)
    prompt = SANITY_CHECK_PROMPT.format(known_terms=known_terms_str)

    print(f"Known terms: {len(known_terms)} loaded from {known_terms_path}")
    print(f"Running sanity pass via {args.engine}...")

    kwargs = {"model": args.model} if args.model else {}
    if args.engine == "anthropic":
        response = summarize_anthropic(transcript_text, prompt, **kwargs)
    else:
        response = summarize_ollama(transcript_text, prompt, **kwargs)

    flags = parse_flags(response)
    report = build_sanity_report(flags, flat_words)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(report, encoding="utf-8")
        print(f"Written: {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
