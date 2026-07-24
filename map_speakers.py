#!/usr/bin/env python3
"""
map_speakers.py
---------------
Approach 2 of the speaker-name injection design map (WATERSHED 2026-07-24):
derive real names for a WhisperX transcript's SPEAKER_XX labels by aligning
it against a reference transcript that already carries names — typically
Zoom's `.transcript.vtt`, whose speaker attribution comes from per-account
audio streams rather than from voice clustering.

This is text-alignment name transfer, NOT voice matching. The two
transcripts are aligned word by word; wherever they agree on a word, the
reference's speaker name casts one vote for the pipeline's label. A label
whose votes are dominated by one name is that person. A label whose votes
are split means diarization merged two or more people into it — the vote
share self-reports that, which is the property that makes this safe.

Usage:
    # Zoom VTT straight in; writes names into .speaker-cache.json, where
    # summarize_transcript.py picks them up automatically
    python3 map_speakers.py meeting.transcript.vtt meeting.json --write-cache

    # Inspect first, write nothing
    python3 map_speakers.py meeting.transcript.vtt meeting.json

    # Reference already converted to WhisperX-shaped JSON
    python3 map_speakers.py zoom_converted.json meeting.json

    # Just convert a VTT, for diffing Zoom against the pipeline with
    # compare_transcripts.py
    python3 map_speakers.py meeting.transcript.vtt --convert-only \
        --out zoom_converted.json

Proven on the ESIIL course session (2026-07-14): the lecturer's two labels
mapped at ~99.7%, while two merged buckets came back at 42% and 29% — the
tool announced its own uncertainty exactly where diarization had failed.

No external dependencies — standard library only. Requires
review_transcript.py and compare_transcripts.py in the same directory.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from compare_transcripts import flatten_words, normalize
from review_transcript import (
    load_segments,
    load_speaker_cache,
    parse_subject,
    save_speaker_cache,
    SPEAKER_CACHE_FILENAME,
)

# Below this vote share, a proposed name is reported but NOT written to the
# cache. The ESIIL run put clean mappings at ~99.7% and merged clusters at
# 42%/29%, so the gap is wide and 80% sits comfortably in it. The whole
# point of the threshold is that a merged label must not silently acquire
# one of the names it merged: a wrong name is worse than SPEAKER_XX,
# because a wrong one does not invite the double-check an anonymous one
# does.
DEFAULT_MIN_SHARE = 80.0


# ── Zoom WebVTT → WhisperX-shaped JSON ────────────────────────────────

TIMESTAMP_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})\s*-->\s*"
    r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})"
)
# Zoom's transcript.vtt prefixes each cue with "Display Name (affil): text".
# Bounded and colon-terminated near the start so ordinary sentence colons
# are not mistaken for speaker prefixes.
SPEAKER_RE = re.compile(r"^([^:]{1,60}?):\s+(.*)$", re.DOTALL)


def parse_ts(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _parse_block(block: list[str]) -> dict | None:
    match = None
    ts_idx = None
    for i, line in enumerate(block):
        match = TIMESTAMP_RE.search(line)
        if match:
            ts_idx = i
            break
    if ts_idx is None:
        return None  # WEBVTT header / NOTE blocks

    g = match.groups()
    start = parse_ts(g[0], g[1], g[2], g[3])
    end = parse_ts(g[4], g[5], g[6], g[7])
    text = " ".join(block[ts_idx + 1:]).strip()
    if not text:
        return None

    speaker = "UNKNOWN"
    sm = SPEAKER_RE.match(text)
    if sm:
        speaker, text = sm.group(1).strip(), sm.group(2).strip()
    return {"start": start, "end": end, "speaker": speaker, "text": text}


def parse_vtt(path: Path) -> list[dict]:
    """Parse a WebVTT file into cue dicts. utf-8-sig strips Zoom's BOM."""
    cues = []
    block: list[str] = []
    lines = path.read_text(encoding="utf-8-sig").splitlines() + [""]
    for raw_line in lines:
        line = raw_line.strip()
        if line:
            block.append(line)
            continue
        if block:
            cue = _parse_block(block)
            if cue:
                cues.append(cue)
            block = []
    return cues


def to_whisperx_shape(cues: list[dict]) -> dict:
    """
    Reshape cues so the existing tools can read them unmodified.

    Honest limitation: VTT carries cue-level timing only, so per-word start
    times are linearly interpolated across each cue. Good enough to locate
    a divergence or cast an alignment vote; not good enough to clip audio
    against.
    """
    segments = []
    for cue in cues:
        tokens = cue["text"].split()
        duration = max(cue["end"] - cue["start"], 0.0)
        step = duration / max(len(tokens), 1)
        words = [
            {
                "word": tok,
                "start": round(cue["start"] + i * step, 3),
                "speaker": cue["speaker"],
            }
            for i, tok in enumerate(tokens)
        ]
        segments.append({
            "start": cue["start"],
            "end": cue["end"],
            "speaker": cue["speaker"],
            "text": cue["text"],
            "words": words,
        })
    return {"segments": segments, "source": "zoom-vtt (converted)"}


def load_reference(path: Path) -> list[dict]:
    """Load a named reference transcript from either .vtt or .json."""
    if path.suffix.lower() == ".vtt":
        cues = parse_vtt(path)
        if not cues:
            raise ValueError(f"No cues parsed from {path} — is it WebVTT?")
        data = to_whisperx_shape(cues)
        tmp = {"segments": data["segments"]}
        return _segments_from_dict(tmp)
    return load_segments(path)


def _segments_from_dict(data: dict) -> list[dict]:
    """load_segments() equivalent for an already-parsed dict."""
    out = []
    for seg in data.get("segments", []):
        words = [
            {
                "w": w.get("word", ""),
                "s": round(w.get("score", 1.0), 3),
                "spk": w.get("speaker", seg.get("speaker", "UNKNOWN")),
                "t": w.get("start"),
            }
            for w in seg.get("words", [])
        ]
        out.append({
            "start": round(seg.get("start", 0), 2),
            "end": round(seg.get("end", 0), 2),
            "speaker": seg.get("speaker", "UNKNOWN"),
            "logprob": round(seg.get("avg_logprob", 0), 3),
            "words": words,
        })
    return out


# ── Alignment and voting ──────────────────────────────────────────────

def vote_names(ref_words: list[dict], pipe_words: list[dict]) -> dict:
    """
    Align two word lists and tally reference speaker names per pipeline
    label.

    Returns {pipeline_label: Counter(reference_name -> votes)}. Only words
    the two transcripts agree on vote, so disagreements (mistranscriptions,
    dropped filler) are simply skipped rather than casting noisy votes.
    """
    norm_ref = [normalize(w["w"]) for w in ref_words]
    norm_pipe = [normalize(w["w"]) for w in pipe_words]
    matcher = SequenceMatcher(None, norm_pipe, norm_ref, autojunk=False)

    votes: dict[str, Counter] = defaultdict(Counter)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            continue
        for offset in range(i2 - i1):
            pipe_spk = pipe_words[i1 + offset]["spk"]
            ref_spk = ref_words[j1 + offset]["spk"]
            if ref_spk and ref_spk != "UNKNOWN":
                votes[pipe_spk][ref_spk] += 1
    return dict(votes)


def summarize_votes(votes: dict, min_share: float = DEFAULT_MIN_SHARE):
    """
    Turn raw votes into per-label proposals with a confident/uncertain
    verdict.

    Returns a list of dicts sorted by label, each with: label, name, share,
    total, runners_up, confident.
    """
    rows = []
    for label in sorted(votes):
        counter = votes[label]
        total = sum(counter.values())
        if not total:
            continue
        name, count = counter.most_common(1)[0]
        share = count / total * 100
        rows.append({
            "label": label,
            "name": name,
            "share": share,
            "total": total,
            "runners_up": [
                (n, c / total * 100) for n, c in counter.most_common(4)[1:]
            ],
            "confident": share >= min_share,
        })
    return rows


# ── CLI ───────────────────────────────────────────────────────────────

def _convert_only(ref_path: Path, out: str | None) -> None:
    cues = parse_vtt(ref_path)
    if not cues:
        print(f"Error: no cues parsed from {ref_path} — is it WebVTT?",
              file=sys.stderr)
        sys.exit(1)
    data = to_whisperx_shape(cues)
    out_path = (Path(out).expanduser().resolve() if out
                else ref_path.with_suffix(".json"))
    out_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    speakers = sorted({c["speaker"] for c in cues})
    n_words = sum(len(s["words"]) for s in data["segments"])
    print(f"Parsed {len(cues)} cues, {n_words} words")
    print(f"Speakers: {', '.join(speakers)}")
    print(f"Written: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Derive real speaker names by aligning a WhisperX transcript "
            "against a named reference transcript (e.g. Zoom's VTT)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python3 map_speakers.py meeting.transcript.vtt meeting.json
  python3 map_speakers.py meeting.transcript.vtt meeting.json --write-cache
  python3 map_speakers.py meeting.transcript.vtt --convert-only
        """,
    )
    parser.add_argument(
        "reference",
        help="Named reference transcript: Zoom .vtt, or WhisperX-shaped .json",
    )
    parser.add_argument(
        "transcript", nargs="?", default=None,
        help="This pipeline's WhisperX .json (omit only with --convert-only)",
    )
    parser.add_argument(
        "--write-cache", action="store_true",
        help=(
            "Write confident mappings into .speaker-cache.json next to the "
            "transcript, where summarize_transcript.py reads them "
            "automatically. Uncertain labels are reported but never written."
        ),
    )
    parser.add_argument(
        "--min-share", type=float, default=DEFAULT_MIN_SHARE,
        help=(
            f"Vote share required to treat a mapping as confident "
            f"(default: {DEFAULT_MIN_SHARE:.0f}%%). Below this, diarization "
            f"probably merged two speakers into one label."
        ),
    )
    parser.add_argument(
        "--subject", default=None,
        help="Override the cache key (default: parsed from the filename)",
    )
    parser.add_argument(
        "--convert-only", action="store_true",
        help="Only convert the VTT to WhisperX-shaped JSON and exit",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output path for --convert-only (default: same stem + .json)",
    )
    args = parser.parse_args()

    ref_path = Path(args.reference).expanduser().resolve()
    if not ref_path.exists():
        print(f"Error: file not found: {ref_path}", file=sys.stderr)
        sys.exit(1)

    if args.convert_only:
        _convert_only(ref_path, args.out)
        return

    if not args.transcript:
        print("Error: a transcript is required unless --convert-only is used.",
              file=sys.stderr)
        sys.exit(1)

    pipe_path = Path(args.transcript).expanduser().resolve()
    if not pipe_path.exists():
        print(f"Error: file not found: {pipe_path}", file=sys.stderr)
        sys.exit(1)

    try:
        ref_words = flatten_words(load_reference(ref_path))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    pipe_words = flatten_words(load_segments(pipe_path))

    print(f"Reference:  {ref_path.name}  ({len(ref_words):,} words)")
    print(f"Transcript: {pipe_path.name}  ({len(pipe_words):,} words)\n")

    votes = vote_names(ref_words, pipe_words)
    if not votes:
        print("No aligned words carried a speaker name — is the reference "
              "the speaker-attributed transcript (.transcript.vtt) rather "
              "than the plain captions (.cc.vtt)?", file=sys.stderr)
        sys.exit(1)

    rows = summarize_votes(votes, args.min_share)
    print(f"{'label':<12} {'proposed name':<34} {'share':>7} {'votes':>7}")
    print("-" * 64)
    for r in rows:
        flag = "" if r["confident"] else "  ← uncertain, not written"
        print(f"{r['label']:<12} {r['name']:<34} {r['share']:6.1f}% "
              f"{r['total']:7,}{flag}")
        if r["runners_up"]:
            also = ", ".join(f"{n} {s:.0f}%" for n, s in r["runners_up"])
            print(f"{'':<12} also: {also}")

    confident = {r["label"]: r["name"] for r in rows if r["confident"]}
    uncertain = [r for r in rows if not r["confident"]]

    if uncertain:
        print(f"\n{len(uncertain)} label(s) below {args.min_share:.0f}% — "
              "diarization probably merged speakers there. Left as "
              "SPEAKER_XX on purpose: an anonymous label invites a check, "
              "a wrong name does not.")

    subject = args.subject or parse_subject(pipe_path)

    if not confident:
        print("\nNothing confident enough to write.")
        return

    if args.write_cache:
        cache_path = pipe_path.parent / SPEAKER_CACHE_FILENAME
        cache = load_speaker_cache(cache_path)
        cache.setdefault(subject, {}).update(confident)
        save_speaker_cache(cache_path, cache)
        print(f"\nWrote {len(confident)} name(s) for subject {subject!r} "
              f"to {cache_path}")
        print("summarize_transcript.py will now pick these up automatically.")
    else:
        pairs = ",".join(f"{k}={v}" for k, v in sorted(confident.items()))
        print(f"\nNothing written (add --write-cache). Subject: {subject!r}")
        print("Equivalent manual step:")
        print(f'  python3 review_transcript.py "{pipe_path}" \\')
        print(f'    --save-speakers "{pairs}"')


if __name__ == "__main__":
    main()
