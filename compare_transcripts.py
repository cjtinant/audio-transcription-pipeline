#!/usr/bin/env python3
"""
compare_transcripts.py
-----------------------
Word-level diff between two WhisperX JSON transcripts of the *same*
recording (e.g. produced by different models) — automates what the
large-v2/v3 comparison did by hand: where do the two outputs actually
disagree, and how much do they agree overall.

Usage:
    python3 compare_transcripts.py transcript_a.json transcript_b.json
    python3 compare_transcripts.py transcript_a.json transcript_b.json --out report.txt

Comparison runs on normalized word text (lowercased, punctuation stripped)
so trivial casing/punctuation differences don't count as disagreements —
only words actually spoken differently do. Reported text keeps the
original casing/punctuation. Timestamps come from each word's own aligned
start time (see review_transcript.py's --report fix), falling back to the
segment start for words that weren't individually aligned.

Reports two agreement metrics: raw (all words) and content (filler/backchannel
words — "um", "yeah", "okay", etc. — removed from both sides before
comparing). The two numbers together are a confidence signal in their own
right: a big gap between them means most of the disagreement is stylistic
(filler dropped, backchannel added), not actual content divergence. The
disagreement list shown is based on the content comparison, since that's
the one worth spot-checking — filler-only differences are expected model
behavior, not something to verify against the audio.

Deliberately does NOT filter by confidence score. The motivating case for
this whole feature (a word both models transcribe differently while both
report high confidence) is exactly what confidence-based filtering would
hide.

Does not require either transcript to be a "reference" — disagreements are
reported as A-says / B-says, not right/wrong. Deciding which (if either) is
correct is still a human judgment call, same as the manual comparison.

No external dependencies — standard library only (difflib for sequence
alignment). Requires review_transcript.py in the same directory (reuses
load_segments so both tools parse WhisperX JSON identically).
"""

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from review_transcript import load_segments


def flatten_words(segments: list[dict]) -> list[dict]:
    """Flatten a transcript's segments into one chronological word list."""
    flat = []
    for seg in segments:
        for w in seg.get("words", []):
            flat.append({
                "w": w["w"],
                "t": w["t"] if w.get("t") is not None else seg.get("start", 0),
                "spk": w.get("spk", seg.get("speaker", "UNKNOWN")),
            })
    return flat


def normalize(word: str) -> str:
    """Lowercase, strip punctuation (keep apostrophes for contractions)."""
    return re.sub(r"[^\w']", "", word.lower())


def fmt_time(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


# Backchannel/filler words dropped from the "content" comparison. Grounded
# in the already-documented large-v2/v3 behavior (large-v3 drops short
# backchannel filler that large-v2 keeps) — not a guessed equivalence
# table, and deliberately narrow: it removes tokens, it doesn't try to
# match "ok"<->"okay" or "gonna"<->"going to" style variants, which are a
# separate (and harder to do safely) normalization problem.
FILLER_WORDS = {"um", "uh", "yeah", "yep", "okay", "ok", "right", "so"}


def strip_filler(words: list[dict]) -> list[dict]:
    """Drop filler/backchannel words entirely from a word list."""
    return [w for w in words if normalize(w["w"]) not in FILLER_WORDS]


def compute_agreement(words_a: list[dict], words_b: list[dict]):
    """Align two word lists with difflib and return (pct, equal, total, opcodes)."""
    norm_a = [normalize(w["w"]) for w in words_a]
    norm_b = [normalize(w["w"]) for w in words_b]
    matcher = SequenceMatcher(None, norm_a, norm_b, autojunk=False)
    opcodes = matcher.get_opcodes()
    equal = sum(i2 - i1 for tag, i1, i2, j1, j2 in opcodes if tag == "equal")
    total = max(len(norm_a), len(norm_b))
    pct = (equal / total * 100) if total else 100.0
    return pct, equal, total, opcodes


def build_diff_report(
    words_a: list[dict], words_b: list[dict], label_a: str, label_b: str
) -> str:
    raw_pct, raw_equal, raw_total, _ = compute_agreement(words_a, words_b)

    content_a = strip_filler(words_a)
    content_b = strip_filler(words_b)
    content_pct, content_equal, content_total, content_opcodes = compute_agreement(
        content_a, content_b
    )

    blocks = []
    for tag, i1, i2, j1, j2 in content_opcodes:
        if tag == "equal":
            continue
        span_a = " ".join(w["w"] for w in content_a[i1:i2]) or "(nothing)"
        span_b = " ".join(w["w"] for w in content_b[j1:j2]) or "(nothing)"
        # Timestamp from whichever side actually has a word in this span.
        ts_source = None
        if i1 < len(content_a):
            ts_source = content_a[i1]
        elif j1 < len(content_b):
            ts_source = content_b[j1]
        ts = fmt_time(ts_source["t"]) if ts_source else "?:??"
        blocks.append(
            f"[{ts}] {tag}\n"
            f"    {label_a}: {span_a!r}\n"
            f"    {label_b}: {span_b!r}"
        )

    header_lines = [
        f"{label_a} ({len(words_a)} words) vs {label_b} ({len(words_b)} words)",
        f"Raw agreement:     {raw_pct:.1f}% ({raw_equal}/{raw_total} words, filler included)",
        f"Content agreement: {content_pct:.1f}% ({content_equal}/{content_total} words, filler removed)",
        f"Disagreements shown: {len(blocks)} (filler-only differences excluded)",
    ]
    header = "\n".join(header_lines)
    header += "\n" + "=" * max(len(l) for l in header_lines)

    if not blocks:
        return header + "\n\n(no disagreements found)"
    return header + "\n\n" + "\n\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Word-level diff between two WhisperX JSON transcripts of the "
            "same recording."
        )
    )
    parser.add_argument("json_a", help="First transcript (e.g. large-v2 output)")
    parser.add_argument("json_b", help="Second transcript (e.g. large-v3 output)")
    parser.add_argument(
        "--out", default=None,
        help="Write report to this path (default: print to stdout)"
    )
    args = parser.parse_args()

    path_a = Path(args.json_a).expanduser().resolve()
    path_b = Path(args.json_b).expanduser().resolve()
    for p in (path_a, path_b):
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    words_a = flatten_words(load_segments(path_a))
    words_b = flatten_words(load_segments(path_b))

    report = build_diff_report(words_a, words_b, path_a.stem, path_b.stem)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(report, encoding="utf-8")
        print(f"Written: {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
