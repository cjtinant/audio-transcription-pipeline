#!/usr/bin/env python3
"""
audio-transcription-pipeline/summarize_transcript.py
─────────────────────────────────────────────────────────────────────
Pipeline Step 2: WhisperX JSON → formatted transcript → LLM summary

CLI usage:
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --engine ollama
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type interview
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type custom \
        --prompt "Summarize this grant meeting, focusing on deadlines."
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --no-save
    python summarize_transcript.py --list-types

Long sessions (multi-hour lectures, course recordings):
    # Defaults are already sized for these — claude-opus-5, 16000-token
    # output ceiling. Use --type lecture for course recordings; raise
    # --max-tokens only if a summary still reads as cut off.
    python summarize_transcript.py ~/PROJECTS/audio-transcription-output/lecture.json \
        --type lecture

Interactive usage (Python REPL or script, from the repo folder):
    from summarize_transcript import run_pipeline
    result = run_pipeline("~/PROJECTS/audio-transcription-output/meeting.json")
See "Interactive / script usage" in docs/pipeline-reference.md for more examples.
─────────────────────────────────────────────────────────────────────
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Output archive default — override by exporting TRANSCRIBE_OUTPUT_DIR
# (the same variable transcribe.sh honors). An explicit --output-dir /
# output_dir argument always wins over both.
DEFAULT_OUTPUT_DIR = os.environ.get(
    "TRANSCRIBE_OUTPUT_DIR", "~/PROJECTS/audio-transcription-output"
)

# ── Model and output-length defaults ──────────────────────────────────
#
# Sized for this pipeline's actual worst case: a multi-hour lecture or
# course session. A 3-hour recording is roughly 40k input tokens once
# speaker labels and timestamps are added (the 2h09m ESIIL session
# measured ~30k — see WATERSHED 2026-07-14).
#
# Model: claude-opus-5. Chosen for long-transcript comprehension —
# 1M-token context, and the freshest knowledge cutoff of the current
# lineup, which matters when a lecture references recent tools or
# events. Override per-run with --model, or set a standing default with
# SUMMARIZE_MODEL (same env-var pattern as TRANSCRIBE_OUTPUT_DIR).
#
# NOTE: this is a reasoned choice, not a measured one. Unlike the
# Anthropic-vs-Ollama engine decision (WATERSHED 2026-07-12), no A/B
# comparison was run across Claude models for this task.
DEFAULT_ANTHROPIC_MODEL = os.environ.get("SUMMARIZE_MODEL", "claude-opus-5")
DEFAULT_OLLAMA_MODEL = os.environ.get(
    "SUMMARIZE_OLLAMA_MODEL", "llama3.1:8b-instruct-q6_k"
)

# Output ceiling per request. The original value (1024) silently
# truncated long summaries: a multi-hour lecture through the six-section
# `grant_planning` or four-section `lecture` preset needs far more than
# ~750 words, and the model has no way to signal it ran out of room.
#
# Sized from measurement, not guesswork: in the 2026-07-24 A/B run
# (ESIIL short course, 2h09m, `lecture`), claude-opus-5 produced 5,976
# output tokens — 73% of an 8192 ceiling. Extrapolated to the 3-hour
# case these defaults exist for, that is ~8,300 tokens, i.e. truncation.
# 16000 restores real headroom. See WATERSHED 2026-07-24.
DEFAULT_MAX_TOKENS = 16000

# Merge combines two full summaries, so its input is roughly twice a
# single summary's output and its own output should not be smaller.
DEFAULT_MERGE_MAX_TOKENS = 16000

# HTTP timeout. The old 60s was set when summaries capped at 1024
# tokens; a large model writing 8k tokens from a 40k-token transcript
# routinely exceeds that. Generous rather than tight — a timeout here
# costs a whole re-run, and the retry logic below only helps for 429/5xx.
DEFAULT_TIMEOUT = 900
DEFAULT_OLLAMA_TIMEOUT = 1800


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
    "grant_planning": "Grant/funding meetings — opportunities, decisions, risks, action items, timeline",
    "custom":    "Provide your own prompt via --prompt or custom_prompt argument",
}


# Approaches 3 and 1 from the WATERSHED design map. Both work by adding
# an instruction block to the prompt rather than by rewriting the
# transcript, so they compose with approach 4: cached names are already
# substituted in the text, and these only address what is left over.
#
# Both are deliberately hedged. WATERSHED's Tier 4 note is explicit that a
# confidently wrong name is worse than SPEAKER_00, because a wrong label
# does not get double-checked the way an anonymous one does. Every
# inferred name is therefore required to carry a marker.

ROSTER_PROMPT = (
    "\nSpeaker identification:\n"
    "The following people attended this meeting:\n{roster}\n"
    "Some speakers are labeled SPEAKER_00, SPEAKER_01 and so on because "
    "automatic diarization could not name them. Where the conversation "
    "makes a speaker's identity clear — someone is addressed by name, or "
    "introduces themselves — you may attribute that speaker using ONLY "
    "names from the list above. Never use a name that is not on the list, "
    "and never guess to fill a gap.\n"
    "Mark every such attribution as '(inferred)' the first time you use "
    "it, e.g. 'Jason (inferred)'. If you cannot tell who a speaker is, "
    "keep the SPEAKER_XX label — an unnamed speaker is a correct answer, "
    "a wrong name is not.\n\n"
)

INFER_PROMPT = (
    "\nSpeaker identification:\n"
    "Speakers are labeled SPEAKER_00, SPEAKER_01 and so on because "
    "automatic diarization could not name them. If the conversation makes "
    "a speaker's identity unambiguous — they are addressed by name "
    "repeatedly, or they introduce themselves — you may attribute that "
    "speaker by name.\n"
    "Mark every such attribution as '(inferred)' the first time you use "
    "it, e.g. 'Jason (inferred)'. Attribute only on clear evidence. If in "
    "any doubt, keep the SPEAKER_XX label — an unnamed speaker is a "
    "correct answer, a wrong name is not.\n\n"
)


def build_speaker_prompt(roster: list[str] | None = None,
                         infer: bool = False) -> str:
    """
    Return the speaker-identification block to append to a prompt.

    A roster (approach 3) beats bare inference (approach 1) whenever both
    are requested: a closed vocabulary cannot invent a name, so there is
    no case where the unconstrained version is preferable.
    """
    if roster:
        return ROSTER_PROMPT.format(
            roster="\n".join(f"- {name}" for name in roster)
        )
    if infer:
        return INFER_PROMPT
    return ""


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


# ── 2b. Speaker-name injection ────────────────────────────────────────
#
# Approach 4 of the five mapped in WATERSHED (2026-07-24): deterministic
# substitution from the cache `review_transcript.py --save-speakers`
# already writes. No inference, so no misattribution — a label either has
# a saved name or it keeps SPEAKER_XX.
#
# Why this exists: the MEFA run showed the most-named person in a
# transcript (11 mentions) absent from both models' summaries, because
# nothing ever told either model who SPEAKER_04 was. Without this, every
# multi-party summary is structurally anonymous regardless of model.

SPEAKER_CACHE_FILENAME = ".speaker-cache.json"


def parse_subject(input_path: str) -> str:
    """
    Subject slug from the yyyy-mm-dd_subject-name(_audio)? convention.

    Deliberately duplicates review_transcript.py's parse_subject rather
    than importing it: that module pulls in subprocess and the HTML
    template for a six-line regex, and the summarizer has no other reason
    to depend on the review tool. The convention is stable and documented
    in the README; if it ever changes, both need updating — noted here so
    the duplication is a choice rather than a surprise.
    """
    stem = Path(input_path).stem
    stem = re.sub(r"_(large-v2|large-v3)$", "", stem)
    m = re.match(r"^\d{4}-\d{2}-\d{2}_(.+)$", stem)
    rest = m.group(1) if m else stem
    rest = re.sub(r"^audio_", "", rest)
    rest = re.sub(r"_audio$", "", rest)
    return rest


def load_speaker_names(input_path: str, subject: str | None = None) -> dict:
    """
    Look up saved speaker names for this transcript's subject.

    Reads `.speaker-cache.json` next to the input file — the same file
    review_transcript.py writes and pre-fills from. Missing or corrupt
    cache means "no names", never an error: a summary without names is
    the old behavior, and failing the run over a cosmetic lookup would be
    worse than the problem it solves.

    Returns:
        Dict of SPEAKER_XX -> name, empty if nothing is cached.
    """
    path = Path(input_path).expanduser()
    cache_path = path.parent / SPEAKER_CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    names = cache.get(subject or parse_subject(input_path), {})
    return names if isinstance(names, dict) else {}


def parse_speaker_pairs(spec: str) -> dict:
    """
    Parse "SPEAKER_00=Jason,SPEAKER_02=Liz" into a dict.

    Same syntax as review_transcript.py --save-speakers, so a mapping can
    be pasted between the two tools without rewriting it.
    """
    pairs = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"Expected SPEAKER_XX=Name, got {item!r}")
        key, _, name = item.partition("=")
        key, name = key.strip(), name.strip()
        if key and name:
            pairs[key] = name
    return pairs


def apply_speaker_names(segments: list[dict], names: dict) -> list[dict]:
    """
    Replace speaker labels with real names where one is known.

    Returns new dicts — the caller's segments are left alone, since
    run_pipeline hands the same list back to the caller in its result.
    Labels with no cached name keep SPEAKER_XX rather than being blanked:
    an unlabeled speaker is honest, a wrongly-labeled one is not.
    """
    if not names:
        return segments
    return [{**seg, "speaker": names.get(seg["speaker"], seg["speaker"])}
            for seg in segments]


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

# Retryable statuses: 429 (rate limit — token-per-minute windows reset
# each minute, so the default wait is 60s), plus transient server errors.
# Found the hard way on a 2h09m transcript (2026-07-14): --merge fires
# two ~30k-token requests back-to-back and the second gets a 429.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 529}


def _post_with_retry(url, *, headers=None, json=None, timeout=DEFAULT_TIMEOUT,
                     max_attempts=4, _post=None, _sleep=time.sleep):
    """
    httpx.post with retry on rate limits and transient server errors.
    Honors the Retry-After header when present (capped at 120s);
    otherwise waits 60s for 429 and briefly for 5xx. Raises via
    raise_for_status() once attempts are exhausted, same as before.
    (_post/_sleep are injection points for unit tests only.)
    """
    if _post is None:
        import httpx
        _post = httpx.post

    for attempt in range(1, max_attempts + 1):
        response = _post(url, headers=headers, json=json, timeout=timeout)
        if response.status_code in _RETRYABLE_STATUSES and attempt < max_attempts:
            retry_after = response.headers.get("retry-after", "")
            if retry_after.isdigit():
                wait = min(int(retry_after), 120)
            elif response.status_code == 429:
                wait = 60
            else:
                wait = 5 * attempt
            print(f"  API returned {response.status_code}; waiting {wait}s "
                  f"before retry ({attempt}/{max_attempts - 1} retries)...")
            _sleep(wait)
            continue
        response.raise_for_status()
        return response

def extract_text(payload: dict) -> str:
    """
    Pull the assistant's text out of an Anthropic Messages response.

    `content` is a LIST OF BLOCKS, not a single text block, and text is
    not guaranteed to be first. Models with adaptive thinking may emit a
    `thinking` block ahead of the answer, in which case the old
    `content[0]["text"]` raised KeyError: 'text'. Because thinking engages
    adaptively, that failed intermittently rather than every time — the
    same request could work twice and crash on the third run.

    Concatenates every text block in order and ignores the rest.
    """
    blocks = payload.get("content") or []
    parts = [
        b.get("text", "") for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    if not parts:
        # Be forgiving about an unfamiliar block shape before giving up.
        parts = [
            b["text"] for b in blocks
            if isinstance(b, dict) and isinstance(b.get("text"), str)
        ]
    text = "\n".join(p for p in parts if p).strip()
    if text:
        return text

    # No text at all. Report enough to diagnose it without a re-run.
    kinds = [b.get("type", "?") for b in blocks if isinstance(b, dict)]
    stop = payload.get("stop_reason")
    detail = f"block types: {kinds or 'none'}; stop_reason: {stop}"
    if stop == "max_tokens":
        raise ValueError(
            "The model hit the output ceiling before producing any text "
            f"({detail}). With adaptive thinking, reasoning tokens draw "
            "on the same budget — raise --max-tokens and retry."
        )
    raise ValueError(f"No text block in the API response ({detail}).")


def summarize_anthropic(
    transcript: str,
    prompt: str,
    model: str = DEFAULT_ANTHROPIC_MODEL,
    api_key: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Summarize a transcript using the Anthropic API.

    Args:
        transcript: Formatted transcript string
        prompt:     System prompt from get_prompt()
        model:      Anthropic model ID (default: DEFAULT_ANTHROPIC_MODEL,
                    currently claude-opus-5; SUMMARIZE_MODEL overrides)
        api_key:    Anthropic API key (default: ANTHROPIC_API_KEY env var)
        max_tokens: Output ceiling for this request. Long transcripts need
                    a large value — the old 1024 truncated multi-hour
                    lecture summaries mid-section without any error.
        timeout:    Per-request HTTP timeout in seconds

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
            "Export it in your shell session (add to ~/.zshrc / ~/.bashrc "
            "to persist):\n"
            "  export ANTHROPIC_API_KEY=sk-ant-yourkey\n"
            "If the key is stored in ~/.Renviron (this pipeline's token "
            "file), export it from there:\n"
            "  export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY "
            "~/.Renviron | cut -d= -f2 | tr -d '\\r')"
        )

    full_prompt = prompt + "Transcript:\n" + transcript

    response = _post_with_retry(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      model,
            "max_tokens": max_tokens,
            "messages":   [{"role": "user", "content": full_prompt}],
        },
        timeout=timeout,
    )
    return extract_text(response.json())


def summarize_ollama(
    transcript: str,
    prompt: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    host: str = "http://127.0.0.1:11434",
    timeout: int = DEFAULT_OLLAMA_TIMEOUT,
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
            timeout=timeout,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    """
    Save summary to disk. Transcript copy is skipped when input is already
    a cleaned .txt — the input file is the transcript.

    Args:
        transcript:  Formatted transcript string
        summary:     LLM summary string
        input_path:  Input file path (used to derive output filenames)
        output_dir:  Directory to save outputs (private archive, flat —
                     not the pipeline repo's own folder)

    Returns:
        Dict with keys: transcript_path (None if input was .txt), summary_path
    """
    out = Path(output_dir).expanduser()
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


# ── 5b. Shared transcript preparation ─────────────────────────────────

def prepare_transcript(
    input_path: str,
    speaker_names: dict | None = None,
    subject: str | None = None,
    use_cache: bool = True,
) -> tuple[list[dict] | None, str]:
    """
    Read a transcript and apply approach-4 speaker names to it.

    Shared by run_pipeline and run_pipeline_merged, which previously
    carried identical parse blocks — one place to change means the two
    paths cannot drift apart on name handling.

    Precedence: an explicit `speaker_names` mapping wins over the cache,
    so a caller can always override what was saved without editing the
    cache file.

    A cleaned .txt input is passed through untouched: it has no speaker
    labels to substitute, and a human already had the chance to write
    real names into it.
    """
    if Path(input_path).suffix.lower() == ".txt":
        print("── Reading cleaned transcript (.txt) ───────")
        return None, read_txt_transcript(input_path)

    print("── Parsing transcript (.json) ──────────────")
    segments = read_whisperx(input_path)

    names = dict(speaker_names) if speaker_names else {}
    if use_cache and not names:
        names = load_speaker_names(input_path, subject)

    if names:
        labels = {seg["speaker"] for seg in segments}
        applied = {k: v for k, v in names.items() if k in labels}
        unmatched = sorted(labels - set(applied))
        if applied:
            print("── Speaker names ───────────────────────────")
            for label, name in sorted(applied.items()):
                print(f"  {label} -> {name}")
            if unmatched:
                print(f"  unnamed, left as-is: {', '.join(unmatched)}")
        segments = apply_speaker_names(segments, applied)

    return segments, format_transcript(segments)


# ── 6. Full pipeline ──────────────────────────────────────────────────

def run_pipeline(
    input_path: str,
    engine: str = "anthropic",
    meeting_type: str = "general",
    custom_prompt: str | None = None,
    save: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    speaker_names: dict | None = None,
    subject: str | None = None,
    use_cache: bool = True,
    roster: list[str] | None = None,
    infer_speakers: bool = False,
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
        output_dir:    Directory for saved outputs (private archive, flat)
        model:         Override the default LLM model name
        max_tokens:    Output ceiling (Anthropic only; Ollama has no
                       equivalent knob in this pipeline's request shape)
        speaker_names: Explicit SPEAKER_XX -> name mapping. Wins over the
                       cache. (Approach 4)
        subject:       Override the cache lookup key, normally parsed from
                       the filename convention
        use_cache:     Read .speaker-cache.json for names (default True)
        roster:        Attendee names; the LLM may attribute speakers using
                       only these, marked '(inferred)'. (Approach 3)
        infer_speakers: Let the LLM infer names from the conversation with
                       no roster to constrain it. Off by default — the
                       least reliable path. (Approach 1)

    Returns:
        Dict with keys: segments, transcript, summary, paths (if saved)

    Examples:
        # Cleaned .txt — recommended path
        result = run_pipeline("~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt",
                              engine="anthropic",
                              meeting_type="general")

        # Raw JSON — quick path, no human review
        result = run_pipeline("~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.json",
                              engine="anthropic",
                              meeting_type="general")

        # Custom prompt
        result = run_pipeline("~/PROJECTS/audio-transcription-output/2026-07-07_soil-moisture_audio.txt",
                              meeting_type="custom",
                              custom_prompt="List every action item and who owns it.")
    """
    if engine not in ("ollama", "anthropic"):
        raise ValueError("engine must be 'ollama' or 'anthropic'")

    segments, transcript = prepare_transcript(
        input_path, speaker_names, subject, use_cache
    )

    print("── Transcript ──────────────────────────────")
    print(transcript, "\n")

    # Build prompt, plus any speaker-identification instructions
    prompt = get_prompt(meeting_type, custom_prompt)
    prompt += build_speaker_prompt(roster, infer_speakers)

    # Summarize
    print(f"── Summarizing via {engine} ({meeting_type}) ──")
    kwargs = {"model": model} if model else {}
    if engine == "anthropic":
        summary = summarize_anthropic(
            transcript, prompt, max_tokens=max_tokens, **kwargs
        )
    else:
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
    max_tokens: int = DEFAULT_MERGE_MAX_TOKENS,
) -> str:
    """
    Merge two independently generated summaries using an LLM.

    Args:
        summary1:   First summary string
        summary2:   Second summary string
        engine:     LLM backend — "ollama" or "anthropic"
        model:      Override model name
        api_key:    Anthropic API key (default: ANTHROPIC_API_KEY env var)
        host:       Ollama server URL
        max_tokens: Output ceiling for the merged summary. Must be at
                    least as large as a single summary's — the merge is
                    meant to be more complete, not shorter.

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
        response = _post_with_retry(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      model or DEFAULT_ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "messages":   [{"role": "user", "content": full_prompt}],
            },
            timeout=DEFAULT_TIMEOUT,
        )
        return extract_text(response.json())
    else:
        try:
            response = httpx.post(
                f"{host}/api/generate",
                json={
                    "model":  model or DEFAULT_OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                },
                timeout=DEFAULT_OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Start it with: ollama serve")
        return response.json()["response"]


# ── 8. Merged pipeline ────────────────────────────────────────────────

def run_pipeline_merged(
    input_path: str,
    engine: str = "anthropic",
    meeting_type: str = "general",
    custom_prompt: str | None = None,
    save: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    speaker_names: dict | None = None,
    subject: str | None = None,
    use_cache: bool = True,
    roster: list[str] | None = None,
    infer_speakers: bool = False,
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

    segments, transcript = prepare_transcript(
        input_path, speaker_names, subject, use_cache
    )

    prompt = get_prompt(meeting_type, custom_prompt)
    prompt += build_speaker_prompt(roster, infer_speakers)
    kwargs = {"model": model} if model else {}

    print("── Run 1 ───────────────────────────────────")
    if engine == "anthropic":
        summary1 = summarize_anthropic(
            transcript, prompt, max_tokens=max_tokens, **kwargs
        )
    else:
        summary1 = summarize_ollama(transcript, prompt, **kwargs)

    print("── Run 2 ───────────────────────────────────")
    if engine == "anthropic":
        summary2 = summarize_anthropic(
            transcript, prompt, max_tokens=max_tokens, **kwargs
        )
    else:
        summary2 = summarize_ollama(transcript, prompt, **kwargs)

    print("── Merging ─────────────────────────────────")
    # Pass `model` through: without it the merge step silently fell back to
    # the default model even when both summary runs used an override.
    # max_tokens likewise — a merge capped below the summaries it combines
    # would drop content the two runs had already produced.
    summary_merged = merge_summaries(
        summary1, summary2, engine, model=model,
        max_tokens=max(max_tokens, DEFAULT_MERGE_MAX_TOKENS),
    )
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
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --engine ollama
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type interview
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --type custom \\
      --prompt "List every action item and who owns it."
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/meeting.json --model claude-sonnet-5
  python summarize_transcript.py ~/PROJECTS/audio-transcription-output/lecture.json --type lecture
  python summarize_transcript.py --list-types
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
        default="anthropic",
        help="LLM backend (default: anthropic; use ollama for local/private processing)",
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
            f"Override LLM model name. "
            f"Anthropic default: {DEFAULT_ANTHROPIC_MODEL} "
            f"(set SUMMARIZE_MODEL for a standing default). "
            f"Ollama default: {DEFAULT_OLLAMA_MODEL}"
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=(
            f"Output ceiling for the summary, Anthropic only "
            f"(default: {DEFAULT_MAX_TOKENS}). Raise for exhaustive "
            f"summaries of very long sessions; a summary that stops "
            f"mid-sentence means this was hit."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory for saved outputs (default: "
            "~/PROJECTS/audio-transcription-output, or TRANSCRIBE_OUTPUT_DIR "
            "if that env var is set)"
        ),
    )
    speaker_group = parser.add_argument_group(
        "speaker names",
        "Resolve SPEAKER_XX labels to real people. Without any of these, a "
        "multi-party summary can only ever say SPEAKER_00. Listed most "
        "reliable first; see WATERSHED's speaker-name injection design map.",
    )
    speaker_group.add_argument(
        "--speakers",
        default=None,
        metavar="PAIRS",
        help=(
            "Explicit names, comma-separated SPEAKER_XX=Name pairs "
            "(e.g. SPEAKER_00=Jason,SPEAKER_02=Liz). Same syntax as "
            "review_transcript.py --save-speakers. Overrides the cache."
        ),
    )
    speaker_group.add_argument(
        "--subject",
        default=None,
        help=(
            "Override the speaker-cache lookup key (default: parsed from "
            "the filename's yyyy-mm-dd_subject-name convention)"
        ),
    )
    speaker_group.add_argument(
        "--no-speaker-names",
        action="store_true",
        help=(
            "Do not read .speaker-cache.json — summarize with raw "
            "SPEAKER_XX labels, the behavior before names were injected"
        ),
    )
    speaker_group.add_argument(
        "--roster",
        default=None,
        metavar="NAMES",
        help=(
            "Comma-separated attendee names. The model may attribute "
            "speakers using only these names, each marked '(inferred)'. "
            "Use when you know who was present but not which label is "
            "whom — e.g. straight from a calendar invite."
        ),
    )
    speaker_group.add_argument(
        "--infer-speakers",
        action="store_true",
        help=(
            "Let the model infer names from the conversation with no "
            "roster to constrain it. Least reliable option and off by "
            "default: it can invent a name that was never said. Prefer "
            "--speakers or --roster where possible."
        ),
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
            print(f"  {name:<16} {desc}")
        print()
        sys.exit(0)

    if not args.input_path:
        parser.print_help()
        sys.exit(1)

    speaker_names = None
    if args.speakers:
        try:
            speaker_names = parse_speaker_pairs(args.speakers)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    roster = None
    if args.roster:
        roster = [n.strip() for n in args.roster.split(",") if n.strip()]

    fn = run_pipeline_merged if args.merge else run_pipeline
    fn(
        input_path     = args.input_path,
        engine         = args.engine,
        meeting_type   = args.meeting_type,
        custom_prompt  = args.custom_prompt,
        save           = not args.no_save,
        output_dir     = args.output_dir,
        model          = args.model,
        max_tokens     = args.max_tokens,
        speaker_names  = speaker_names,
        subject        = args.subject,
        use_cache      = not args.no_speaker_names,
        roster         = roster,
        infer_speakers = args.infer_speakers,
    )


if __name__ == "__main__":
    main()
