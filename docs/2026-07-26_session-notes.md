# Session notes — 2026-07-26

## Project

`audio-transcription-pipeline` (Ollama infrastructure thread — not pipeline
code, but the local engine option the pipeline depends on for sensitive
material). Short session, run in Cowork while cooking dinner. Single thread:
refresh the local Ollama model stack, following up on the 2026-07-14 research
note's recommendation. Turned into an unplanned uninstall/reinstall detour along
the way.

## Shape of the session

1. Inventory and hardware check
2. Model stack swap (prune → uninstall → reinstall → pull)
3. An install-method gotcha, found by using it
4. Behavioral spot-check across the three new models

## 1. Inventory and hardware check

Existing local store: three `llama3.1:8b` variants at different quantizations
(`q6_K` 6.6GB, `q8_0` 8.5GB, default/`q4` 4.9GB), ~19GB total — confirmed as the
_entire_ model store against `du -sh ~/.ollama/models`. Hardware confirmed as M1
Max, 64GB unified memory (the top M1 Max config) — settles the RAM-adequacy
question the 2026-07-14 research note flagged as needing personal verification,
not just corroborated blog claims. The three small variants had been a hedge
against not being able to run anything larger; no longer needed.

## 2. Model stack swap

Removed all three `llama3.1:8b` variants. Pulled a new three-model stack, chosen
to cover the two stated use cases — sensitive-transcript processing, and
side-by-side testing against Claude:

| Model            | Class    | Tags                           | Role                                                                     |
| ---------------- | -------- | ------------------------------ | ------------------------------------------------------------------------ |
| `qwen3.6:35b`    | ~35B MoE | vision, tools, thinking        | general all-rounder — confirms the 2026-07-14 research note's pick       |
| `nemotron3:33b`  | 33B      | vision, tools, thinking, audio | built for summarization/transcription/document intelligence specifically |
| `granite4.1:30b` | 30B      | tools                          | IBM, Apache 2.0, tuned for RAG/structured output                         |

At Q4-class quantization each runs ~18–25GB — comfortable on 64GB with room to
spare, no need to reach for 70B+.

Also required an Ollama version update: was on 0.15.6 (from the original `.pkg`
install), current is 0.32.x, and the newer model families need the current
engine.

## 3. Install-method gotcha, found by using it

Uninstalling the `.pkg` install (`sudo rm /usr/local/bin/ollama`,
`sudo rm -rf /Applications/Ollama.app`) and reinstalling via Homebrew
(`brew install ollama`, 0.32.4) left `ollama -v` reporting a version mismatch:
new CLI, old server.

Cause: `pkill -x Ollama` only matches the exact process name `Ollama` (capital
O, the menu-bar app). The actual background server is a separate process,
lowercase `ollama` (from `ollama serve`), which pkill's exact-match never
touched — it kept running in memory, still bound to port 11434, even after its
binary file was deleted. Deleting a file doesn't stop a process already using
it.

Fix: `ps aux | grep -i "ollama serve"` / `lsof -i :11434` to find the stale PID,
`kill <PID>`, then `brew services restart ollama`. Full detail captured in
WATERSHED as a gotcha for the next upgrade or install-method switch.

`~/.ollama` (models, logs, ed25519 keypair) was untouched throughout —
uninstalling the binary/app never touches model data.

## 4. Behavioral spot-check

Ran the same trivial prompt (`"Say hello in one sentence."`) against all three,
thinking mode left on by default:

- **qwen3.6:35b** — long, visibly self-correcting chain-of-thought before
  answering (re-litigated whether an em-dash ends a sentence, repeatedly).
  Verbose but not wrong.
- **nemotron3:33b** — one short thinking pass, then committed. Noticeably more
  economical than qwen3.6 for the same task.
- **granite4.1:30b** — no thinking trace at all, direct answer. Consistent with
  it not carrying the "thinking" tag in Ollama's library listing.

Not a rigorous eval — three prompts, one each — but a real first read on
character, not just parameter count, going into actual use.

## Decisions

- Local stack is `qwen3.6:35b`, `nemotron3:33b`, `granite4.1:30b`; all three
  `llama3.1:8b` variants retired.
- Ollama managed via Homebrew going forward, not the `.pkg` installer.
- No pipeline default chosen yet among the three — see WATERSHED (this session
  broke the existing hardcoded default, see below).

## Open, carried forward

- **`summarize_transcript.py`'s `DEFAULT_OLLAMA_MODEL` now points to a deleted
  model** (`llama3.1:8b-instruct-q6_k`). `--engine ollama` with no `--model`
  override will fail until this is fixed or a new default is chosen. Not fixed
  this session — flagged in WATERSHED, decision pending.
- **Cloud-tag verification not yet run.** The 2026-07-14 research note's own
  safety check — `ollama show <model>` to confirm local weights before trusting
  sensitive material to a new model — hasn't been run against any of the three
  new models yet.
- `docs/pipeline-reference.md` still references the retired `llama3.1` variants
  in its install and `--model` override examples (same class of stale-reference
  drift as 2026-07-24's README fixes). Not touched this session — out of scope
  for what was asked.
- Which of the three becomes the actual pipeline default is still open; the
  2026-07-14 note's own suggested method (rerun `sanity_check_transcript.py`
  against a real candidate, not a benchmark-blog number) is the natural next
  step once that question is picked up.
