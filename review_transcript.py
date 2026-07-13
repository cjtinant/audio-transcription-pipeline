#!/usr/bin/env python3
"""
review_transcript.py
--------------------
Convert a WhisperX JSON transcript into an standalone HTML review tool.

Usage:
    python3 review_transcript.py path/to/transcript.json
    python3 review_transcript.py path/to/transcript.json --out path/to/output.html
    python3 review_transcript.py path/to/transcript.json --report
    python3 review_transcript.py path/to/transcript.json --report --threshold 0.15
    python3 review_transcript.py path/to/transcript.json --save-speakers "SPEAKER_00=Jason,SPEAKER_02=Dana"

The HTML file opens in your default browser and lets you:
  - Label speakers by name
  - Flag low-confidence words (adjustable threshold)
  - Search for hot words / key terms
  - Export a labeled plain-text transcript

--report additionally writes a compact text file listing only the
low-confidence words (timestamp, confidence, speaker, surrounding
context) — for jumping straight to trouble spots instead of scanning
the full highlighted transcript.

Speaker-slot caching: the subject slug is parsed from the filename's
yyyy-mm-dd_subject-name convention (override with --subject). Speaker
names saved for a subject are cached in a .speaker-cache.json file next
to the transcript, and pre-filled automatically next time a transcript
with the same subject is opened. Use --save-speakers to record names
for the current subject without regenerating the HTML.

Audio-linked spot-checking: --clip TIMESTAMP ffmpeg-clips a few seconds
of the source audio around a flagged word, e.g. the [M:SS] timestamp
--report just printed. Requires the transcript's source audio path to
be recorded in .source-audio.json (written by transcribe.sh since
2026-07-12 — older transcripts won't have an entry).

    python3 review_transcript.py path/to/transcript.json --clip 2:26
    python3 review_transcript.py path/to/transcript.json --clip 2:26 --clip-padding 5

No external dependencies — standard library only. --clip additionally
requires ffmpeg on PATH (already a pipeline dependency via transcribe.sh).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def load_segments(json_path: Path) -> list[dict]:
    with open(json_path) as f:
        data = json.load(f)

    segments = data.get("segments", [])
    out = []
    for seg in segments:
        words = []
        for w in seg.get("words", []):
            words.append({
                "w": w.get("word", ""),
                "s": round(w.get("score", 1.0), 3),
                "spk": w.get("speaker", seg.get("speaker", "UNKNOWN")),
                # Word's own start time from whisperx's alignment step, not
                # the segment's. Some words (e.g. unaligned punctuation) may
                # lack this — None means "fall back to segment start".
                "t": w.get("start"),
            })
        out.append({
            "start": round(seg.get("start", 0), 2),
            "end": round(seg.get("end", 0), 2),
            "speaker": seg.get("speaker", "UNKNOWN"),
            "logprob": round(seg.get("avg_logprob", 0), 3),
            "words": words,
        })
    return out


def collect_speakers(segments: list[dict]) -> list[str]:
    seen = []
    for seg in segments:
        spk = seg["speaker"]
        if spk not in seen:
            seen.append(spk)
    return sorted(seen)


def build_flagged_report(
    segments: list[dict], threshold: float = 0.2, context_words: int = 4
) -> str:
    """
    Build a compact plain-text report of low-confidence words: timestamp,
    word, confidence, speaker, and a few words of surrounding context — for
    jumping straight to actual trouble spots instead of scanning a full
    highlighted transcript.

    Timestamp is the word's own start time (from whisperx's alignment step),
    not the segment's — a segment can run much longer than a single word, so
    using the segment start would point well before the actual word in
    longer segments. Falls back to segment start only if a word wasn't
    individually aligned.
    """
    lines = []
    for seg in segments:
        words = seg.get("words", [])
        for i, w in enumerate(words):
            score = w.get("s")
            if score is None or score >= threshold:
                continue

            start_ctx = max(0, i - context_words)
            end_ctx = min(len(words), i + context_words + 1)
            tokens = []
            for j in range(start_ctx, end_ctx):
                token = words[j]["w"]
                if j == i:
                    token = f"**{token}**"
                tokens.append(token)
            context = " ".join(tokens)

            word_time = w.get("t")
            ts = word_time if word_time is not None else seg.get("start", 0)
            m, s = divmod(int(ts), 60)
            spk = w.get("spk", seg.get("speaker", "UNKNOWN"))
            lines.append(
                f"[{m}:{s:02d}] {w['w']!r} "
                f"(confidence: {score:.2f}, speaker: {spk})\n"
                f"    {context}"
            )

    header = f"{len(lines)} word(s) below confidence {threshold:.2f}"
    header += "\n" + "=" * len(header)
    if not lines:
        return header + "\n\n(none found)"
    return header + "\n\n" + "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Speaker-slot caching
# ---------------------------------------------------------------------------

SPEAKER_CACHE_FILENAME = ".speaker-cache.json"


def parse_subject(json_path: Path) -> str:
    """
    Extract a subject slug from a filename following the
    yyyy-mm-dd_subject-name(_audio)? naming convention (see README's
    Naming convention section). Also handles the older audio_subject-name
    ordering and strips a trailing _large-v2/_large-v3 comparison suffix.
    Falls back to the full filename stem if nothing matches — caching
    still works, just keyed on a less clean name.
    """
    stem = json_path.stem
    stem = re.sub(r"_(large-v2|large-v3)$", "", stem)
    m = re.match(r"^\d{4}-\d{2}-\d{2}_(.+)$", stem)
    rest = m.group(1) if m else stem
    rest = re.sub(r"^audio_", "", rest)
    rest = re.sub(r"_audio$", "", rest)
    return rest


def load_speaker_cache(cache_path: Path) -> dict:
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_speaker_cache(cache_path: Path, cache: dict) -> None:
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Audio-linked spot-checking
# ---------------------------------------------------------------------------

SOURCE_AUDIO_FILENAME = ".source-audio.json"


def open_with_default_app(path: Path) -> None:
    """
    Open a file with the platform's default application: `open` on macOS,
    `xdg-open` elsewhere (standard on Linux desktops; WSL2 users may need
    the wslu package for it, or can pass --no-open and open files from
    Windows instead).
    """
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(path)], check=False)


def parse_timestamp(ts: str) -> float:
    """
    Parse a timestamp given as M:SS, H:MM:SS, or a plain number of seconds
    into float seconds. Accepts the same [M:SS] format --report prints, so a
    timestamp can be copied straight from one command into the other.
    """
    parts = ts.strip().split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        print(f"Error: could not parse timestamp {ts!r} (expected M:SS, "
              f"H:MM:SS, or seconds)", file=sys.stderr)
        sys.exit(1)

    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        m, s = parts
        return m * 60 + s
    elif len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    else:
        print(f"Error: could not parse timestamp {ts!r} (expected M:SS, "
              f"H:MM:SS, or seconds)", file=sys.stderr)
        sys.exit(1)


def clip_audio(json_path: Path, timestamp: str, padding: float, no_open: bool) -> None:
    """
    Look up the transcript's source audio in .source-audio.json (written by
    transcribe.sh) and ffmpeg-clip a few seconds around `timestamp` — for
    listening to a flagged word directly instead of trusting a confidence
    score alone.
    """
    archive_dir = json_path.parent
    sidecar_path = archive_dir / SOURCE_AUDIO_FILENAME
    # Reuses load_speaker_cache's generic tolerant-JSON-dict-load logic —
    # same shape (missing/corrupt file both mean "empty dict"), different
    # sidecar file.
    source_map = load_speaker_cache(sidecar_path)

    stem = json_path.stem
    audio_path_str = source_map.get(stem)
    if not audio_path_str:
        print(f"Error: no source audio recorded for {stem!r} in "
              f"{sidecar_path}.", file=sys.stderr)
        print("Only transcripts produced by transcribe.sh since the "
              "sidecar fix (2026-07-12) have this — older transcripts "
              "can't be spot-checked this way.", file=sys.stderr)
        sys.exit(1)

    audio_path = Path(audio_path_str)
    if not audio_path.exists():
        print(f"Error: recorded source audio no longer exists: "
              f"{audio_path}", file=sys.stderr)
        sys.exit(1)

    center = parse_timestamp(timestamp)
    start = max(0.0, center - padding)
    end = center + padding

    m, s = divmod(int(center), 60)
    out_path = archive_dir / f"{stem}_clip_{m}m{s:02d}s.wav"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-ss", f"{start:.2f}",
        "-to", f"{end:.2f}",
        str(out_path),
    ]
    print(f"Clipping {audio_path.name} [{start:.1f}s–{end:.1f}s] -> {out_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    print(f"Written: {out_path}")
    if not no_open:
        open_with_default_app(out_path)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;
  color:#1a1a1a;background:#f5f5f2;padding:20px;line-height:1.6}}
h1{{font-size:18px;font-weight:500;margin-bottom:4px;color:#1a1a1a}}
.subtitle{{font-size:12px;color:#888;margin-bottom:16px}}
.controls{{display:flex;flex-wrap:wrap;gap:10px;padding:12px 14px;
  background:#fff;border:0.5px solid #ddd;border-radius:8px;
  margin-bottom:12px;align-items:center}}
.ctrl-group{{display:flex;align-items:center;gap:6px}}
label{{font-size:12px;color:#666;white-space:nowrap}}
input[type=text]{{height:30px;font-size:13px;padding:0 8px;
  border-radius:6px;border:0.5px solid #ccc;background:#fafafa}}
input[type=text]:focus{{outline:none;border-color:#888;background:#fff}}
input[type=range]{{width:90px;accent-color:#555}}
.spk-input{{height:28px;font-size:12px;padding:0 6px;width:120px;
  border-radius:6px;border:0.5px solid #ccc;background:#fafafa}}
.spk-input:focus{{outline:none;border-color:#888}}
button{{font-size:12px;height:28px;padding:0 10px;cursor:pointer;
  border:0.5px solid #ccc;border-radius:6px;background:#fff;color:#333}}
button:hover{{background:#f0f0f0}}
.badge{{display:inline-block;font-size:11px;font-weight:500;
  padding:1px 7px;border-radius:20px;white-space:nowrap}}
.legend{{display:flex;gap:14px;font-size:11px;color:#666;
  padding:6px 0 10px;flex-wrap:wrap;align-items:center}}
.leg-item{{display:flex;align-items:center;gap:4px}}
.leg-swatch{{display:inline-block;width:13px;height:13px;border-radius:3px}}
#transcript-list{{background:#fff;border:0.5px solid #ddd;border-radius:8px;
  padding:0 14px;max-height:75vh;overflow-y:auto}}
.seg{{padding:9px 0;border-bottom:0.5px solid #eee;
  display:flex;gap:12px;align-items:flex-start}}
.seg:last-child{{border-bottom:none}}
.seg.hidden{{display:none}}
.seg-meta{{min-width:88px;max-width:88px;font-size:11px;color:#999;
  font-family:"SF Mono",Consolas,monospace;padding-top:2px;line-height:1.7}}
.seg-body{{flex:1;line-height:1.9}}
.word{{display:inline;cursor:default}}
.low{{background:#fde8e0;border-radius:3px;padding:0 1px}}
.hot{{background:#fef3cd;border-radius:3px;font-weight:600;padding:0 1px}}
.stats{{font-size:12px;color:#888;margin-left:auto}}
.no-results{{color:#aaa;font-size:13px;padding:32px 0;text-align:center}}
.export-bar{{display:flex;justify-content:flex-end;padding:8px 0;gap:8px}}
textarea#export-out{{width:100%;height:300px;font-family:"SF Mono",Consolas,monospace;
  font-size:12px;padding:10px;border:0.5px solid #ccc;border-radius:6px;
  background:#fafafa;display:none;margin-top:8px;resize:vertical}}
</style>
</head>
<body>

<h1>{title}</h1>
<div class="subtitle">{subtitle}</div>

<div class="controls" id="spk-controls">
<!-- speaker label inputs injected by JS -->
</div>

<div class="controls">
  <div class="ctrl-group">
    <label>🔍</label>
    <input type="text" id="hotword" placeholder="Hot word search…" oninput="filterHot()" style="width:180px">
    <button onclick="document.getElementById('hotword').value='';filterHot()">Clear</button>
  </div>
  <div class="ctrl-group">
    <label>Flag below</label>
    <input type="range" id="thresh" min="0" max="0.5" step="0.05" value="0.2" oninput="updateThresh()">
    <span id="thresh-val" style="font-size:12px;min-width:30px;color:#555">0.20</span>
  </div>
  <span class="stats" id="stats"></span>
</div>

<div class="legend" id="legend"></div>

<div class="export-bar">
  <button onclick="exportText()">Export labeled text ↓</button>
</div>
<textarea id="export-out" readonly></textarea>

<div id="transcript-list"></div>

<script>
const SEGS = {segs_json};
const ALL_SPEAKERS = {speakers_json};
const KNOWN_NAMES = {known_names_json};

// Palette: blue, green, amber, coral, purple, teal
const PALETTES = [
  {{bg:'#dbeafe',color:'#1e40af'}},
  {{bg:'#dcfce7',color:'#166534'}},
  {{bg:'#fef9c3',color:'#854d0e'}},
  {{bg:'#ffe4e6',color:'#9f1239'}},
  {{bg:'#ede9fe',color:'#5b21b6'}},
  {{bg:'#ccfbf1',color:'#115e59'}},
];

const spkNames = {{}};
const spkPalette = {{}};
ALL_SPEAKERS.forEach((s,i) => {{
  spkNames[s] = KNOWN_NAMES[s] || s;
  spkPalette[s] = PALETTES[i % PALETTES.length];
}});

let thresh = 0.2, hotword = '';

// Build speaker label inputs
function buildSpeakerControls() {{
  const container = document.getElementById('spk-controls');
  container.innerHTML = '';
  ALL_SPEAKERS.forEach((spk, i) => {{
    const g = document.createElement('div');
    g.className = 'ctrl-group';
    const lbl = document.createElement('label');
    lbl.style.cssText = 'font-size:11px;';
    const pal = spkPalette[spk];
    lbl.innerHTML = `<span class="badge" style="background:${{pal.bg}};color:${{pal.color}}">${{spk}}</span>`;
    const inp = document.createElement('input');
    inp.className = 'spk-input';
    inp.value = spkNames[spk];
    inp.placeholder = spk;
    inp.oninput = () => {{ spkNames[spk] = inp.value || spk; render(); }};
    g.appendChild(lbl);
    g.appendChild(inp);
    container.appendChild(g);
  }});
}}

function buildLegend() {{
  const leg = document.getElementById('legend');
  let html = '';
  ALL_SPEAKERS.forEach(spk => {{
    const p = spkPalette[spk];
    html += `<span class="leg-item"><span class="leg-swatch" style="background:${{p.bg}};border:1px solid ${{p.color}}40"></span> ${{spkNames[spk] || spk}}</span>`;
  }});
  html += `<span class="leg-item"><span class="leg-swatch" style="background:#fde8e0;border:1px solid #f9a8a8"></span> low confidence</span>`;
  html += `<span class="leg-item"><span class="leg-swatch" style="background:#fef3cd;border:1px solid #fcd34d"></span> hot word</span>`;
  leg.innerHTML = html;
}}

function fmtTime(s) {{
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return m + ':' + String(sec).padStart(2, '0');
}}

function updateThresh() {{
  thresh = parseFloat(document.getElementById('thresh').value);
  document.getElementById('thresh-val').textContent = thresh.toFixed(2);
  render();
}}

function filterHot() {{
  hotword = document.getElementById('hotword').value.toLowerCase().trim();
  render();
}}

function render() {{
  buildLegend();
  const list = document.getElementById('transcript-list');
  const hw = hotword;
  let vis = 0, html = '';

  for (const seg of SEGS) {{
    const spk = seg.speaker || 'UNKNOWN';
    const pal = spkPalette[spk] || {{bg:'#eee',color:'#555'}};
    const name = spkNames[spk] || spk;
    let match = false;
    if (hw) {{
      for (const w of seg.words) {{
        if (w.w.toLowerCase().includes(hw)) {{ match = true; break; }}
      }}
    }}
    if (hw && !match) {{ html += '<div class="seg hidden"></div>'; continue; }}
    vis++;

    let whtml = '';
    for (const w of seg.words) {{
      const low = w.s < thresh;
      const hot = hw && w.w.toLowerCase().includes(hw);
      let cls = 'word';
      if (hot) cls += ' hot';
      else if (low) cls += ' low';
      whtml += `<span class="${{cls}}" title="confidence: ${{w.s.toFixed(2)}} | speaker: ${{w.spk}}">${{w.w}} </span>`;
    }}

    const lowSeg = seg.logprob < -0.5;
    const badge = `<span class="badge" style="background:${{pal.bg}};color:${{pal.color}}">${{name}}</span>`;
    const warn = lowSeg ? '<br><span style="color:#dc2626;font-size:10px" title="low segment confidence">⚠ low conf</span>' : '';

    html += `<div class="seg">
      <div class="seg-meta">${{fmtTime(seg.start)}}–${{fmtTime(seg.end)}}<br>${{badge}}${{warn}}</div>
      <div class="seg-body">${{whtml}}</div>
    </div>`;
  }}

  list.innerHTML = html || (hw ? `<div class="no-results">No segments match "${{hw}}"</div>` : '');
  document.getElementById('stats').textContent =
    hw ? `${{vis}} of ${{SEGS.length}} segments` : `${{SEGS.length}} segments`;
}}

function exportText() {{
  const textarea = document.getElementById('export-out');
  const lines = [];
  for (const seg of SEGS) {{
    const name = spkNames[seg.speaker] || seg.speaker;
    const text = seg.words.map(w => w.w).join(' ');
    lines.push(`[${{fmtTime(seg.start)}}] ${{name}}: ${{text}}`);
  }}
  textarea.value = lines.join('\\n');
  textarea.style.display = textarea.style.display === 'none' ? 'block' : 'none';
}}

buildSpeakerControls();
render();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert a WhisperX JSON transcript to a standalone HTML review tool."
    )
    parser.add_argument("json_path", help="Path to WhisperX JSON output file")
    parser.add_argument(
        "--out", default=None,
        help="Output HTML path (default: same directory as input, same stem + .html)"
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Write the file but do not open it in the browser"
    )
    parser.add_argument(
        "--report", action="store_true",
        help=(
            "Also write a compact text report of low-confidence words "
            "(timestamp, confidence, speaker, context) — same directory "
            "as the HTML output, stem + _flagged.txt"
        )
    )
    parser.add_argument(
        "--threshold", type=float, default=0.2,
        help="Confidence threshold for --report (default: 0.2, matches "
             "the HTML tool's default slider position)"
    )
    parser.add_argument(
        "--subject", default=None,
        help=(
            "Override the subject slug used for speaker-name caching "
            "(default: parsed from the filename's "
            "yyyy-mm-dd_subject-name convention)"
        )
    )
    parser.add_argument(
        "--save-speakers", default=None,
        help=(
            "Save speaker names for this subject, comma-separated "
            "SPEAKER_XX=Name pairs (e.g. "
            "SPEAKER_00=Jason,SPEAKER_02=Dana). Updates the cache without "
            "regenerating the HTML — run this after you've decided on "
            "names, so next time they're pre-filled automatically."
        )
    )
    parser.add_argument(
        "--clip", default=None, metavar="TIMESTAMP",
        help=(
            "Spot-check a flagged word: ffmpeg-clip the source audio around "
            "TIMESTAMP (e.g. 2:26, 1:02:26, or seconds — accepts the same "
            "[M:SS] format --report prints). Requires the transcript's "
            "source audio path in .source-audio.json (written by "
            "transcribe.sh since 2026-07-12). Writes a .wav clip next to "
            "the transcript and exits without generating the HTML review."
        )
    )
    parser.add_argument(
        "--clip-padding", type=float, default=3.0,
        help="Seconds of context before/after --clip's timestamp (default: 3.0)"
    )
    args = parser.parse_args()

    json_path = Path(args.json_path).expanduser().resolve()
    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    if args.clip is not None:
        clip_audio(json_path, args.clip, args.clip_padding, args.no_open)
        return

    subject = args.subject or parse_subject(json_path)
    cache_path = json_path.parent / SPEAKER_CACHE_FILENAME
    cache = load_speaker_cache(cache_path)

    if args.save_speakers:
        pairs = {}
        for item in args.save_speakers.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" not in item:
                print(f"Error: expected SPEAKER_XX=Name, got {item!r}", file=sys.stderr)
                sys.exit(1)
            key, _, name = item.partition("=")
            pairs[key.strip()] = name.strip()
        cache.setdefault(subject, {}).update(pairs)
        save_speaker_cache(cache_path, cache)
        print(f"Saved speaker names for subject {subject!r} to {cache_path}:")
        for k, v in pairs.items():
            print(f"  {k} -> {v}")
        return

    known_names = cache.get(subject, {})

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        # Default: same directory as the input JSON, same stem + _review.html.
        # Output lives in a single flat archive folder (no raw/processed
        # split), so no special-casing is needed here.
        out_dir = json_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{json_path.stem}_review.html"

    print(f"Reading:  {json_path}")
    segments = load_segments(json_path)
    speakers = collect_speakers(segments)

    print(f"Segments: {len(segments)}")
    print(f"Speakers: {', '.join(speakers)}")
    if known_names:
        print(f"Subject:  {subject!r} — pre-filled from cache: {known_names}")
    else:
        print(f"Subject:  {subject!r} — no cached speaker names yet")

    title = json_path.stem
    duration_s = segments[-1]["end"] if segments else 0
    m, s = divmod(int(duration_s), 60)
    subtitle = f"{len(segments)} segments · {len(speakers)} speakers · {m}m {s}s"

    html = HTML_TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        segs_json=json.dumps(segments, separators=(",", ":")),
        speakers_json=json.dumps(speakers),
        known_names_json=json.dumps(known_names),
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"Written:  {out_path}")

    if args.report:
        report = build_flagged_report(segments, threshold=args.threshold)
        report_path = out_path.with_name(f"{json_path.stem}_flagged.txt")
        report_path.write_text(report, encoding="utf-8")
        print(f"Report:   {report_path}")
        print()
        print(report)

    if not args.no_open:
        open_with_default_app(out_path)
        print("Opened in browser.")


if __name__ == "__main__":
    main()
