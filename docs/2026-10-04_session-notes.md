# Session notes — 2026-10-04

## Purpose and scope

Review the repository and recommend steps to update and organize it. The
initial review added this note only; the changes below are proposals, not
implemented fixes. A subsequent documentation update records the user's model
pull results here and in WATERSHED. No pipeline code was changed, inference
run, files relocated, or commits created by the assistant.

Reviewed tracked structure, the shell wrapper, Python entry points and tests,
installation/reference documentation, prior session notes, WATERSHED, and local
scratch context. This was a maintenance review, not a full security audit or
end-to-end transcription test. Provider model availability and the current
Ollama installation were not checked during the initial review. The follow-up
below records installation evidence supplied by the user.

## Baseline

- Working tree was clean before this note; HEAD was `c75ac8e`.
- Five Python tools, one transcription wrapper, and five test modules form a
  manageable small project. Keep the existing command paths for now.
- `.venv/bin/python -m unittest discover tests`: **98 tests passed**.
- `bash -n transcribe.sh`: **passed**.
- Tests do not establish that WhisperX, diarization, or either LLM backend works
  end to end. Retry messages and invalid-timestamp errors in test output were
  expected test behavior, not failures.
- Local admin, scratch, staging, archive, and temporary scripts are ignored.
  They are not clutter in the tracked repository and should not be bulk-added.

## Recommended work, in order

### 1. Resolve the local model default and reconcile its documentation

**Finding:** `summarize_transcript.py` still defaults to
`llama3.1:8b-instruct-q6_k`. The July 26 session note and WATERSHED report that
model was removed. If that remains the local state, the default Ollama path
fails without a model override. Current-use examples in
`docs/pipeline-reference.md` and `sanity_check_transcript.py` retain the old
model reference.

**Progress:** installed inventory and same-tag update checks completed by the
user on October 4; see the results below. Evaluation and default selection
remain open.

**Remaining steps:** evaluate candidates on an
appropriate transcript using summarization and sanity checking; record quality,
runtime, and any incomplete output; then select the default and update current
instructions together. Verify the Anthropic default against the provider before
changing or endorsing it. Do not treat historical model names or pricing as
current provider facts.

WATERSHED already contains pasted `ollama show` results after text saying that
check is still pending. Reconcile that evidence instead of repeating every old
task. Its draft commit also says `qwen3.6:36b`, while later text corrects the
tag to `qwen3.6:35b`. Preserve historical notes and record the final decision in
a new dated entry.

**Files:** `summarize_transcript.py`, `sanity_check_transcript.py`,
`docs/pipeline-reference.md`, relevant README examples, `WATERSHED.md`.

**Proposed commit:** `fix: align Ollama default and usage docs with evaluated model`

**Safe to automate:** inventory and consistency checks; model selection needs
evaluation. External calls or sensitive-transcript processing need an explicit
choice of data and backend before execution.

### 2. Separate active work from decision history

**Finding:** `WATERSHED.md` is about 102 KB and combines pending work, resolved
items, pasted conversations, command output, and repeated proposals. It is hard
to tell which recommendations still apply. For example, speaker-cache injection
and promotion of comparison probes need reconciliation with the existing
summarizer, `map_speakers.py`, and tests.

**Steps:** create a short `TASKS.md` with priority, status, affected files, and
completion criteria. Give each active task one canonical entry. Keep WATERSHED
as a decision index and move its lengthy history to a tracked history document,
preserving source dates and links. Do not move shared history into the ignored
`99_archive/` directory. Resolve duplicates by checking code and tests, not just
the wording of older notes.

Add `docs/README.md` as the documentation index. Initially link existing dated
notes where they are; a later move into `docs/session-notes/` is optional and
should include updating links and the README tree.

**Files:** `WATERSHED.md`, new `TASKS.md`, new `docs/README.md`, proposed
`docs/history/watershed-history.md`, `README.md`.

**Proposed commit:** `docs: separate active tasks from decision history`

**Safe to automate:** yes for reversible document edits and link checks;
ambiguous decisions should remain explicitly open.

### 3. Make installation claims match the supported environment

**Finding:** `requirements-lock.txt` describes itself as a July 12 macOS arm64
snapshot, not an install script. `docs/installation.md` presents it as exact
reproduction, says direct dependencies are pinned, and then gives unpinned
installation commands. These describe different levels of reproducibility.
The October 1 scratch log also shows TorchCodec loader warnings, but does not
establish whether the transcription ultimately succeeded or failed.

**Steps:** document the distinction between a tested snapshot and a fresh
installation. Record Python, platform, FFmpeg, Torch, TorchCodec, WhisperX, and
pyannote versions together. Establish a small direct-dependency manifest and a
clear update procedure; decide whether the snapshot should become a maintained
platform-specific lock. Test upgrades in a separate environment before replacing
the working `.venv`. Use a short non-sensitive audio sample to verify decoding,
transcription, and diarization; investigate the warning based on that result.
Avoid simply suppressing warnings or upgrading everything at once.

**Files:** `requirements-lock.txt`, `docs/installation.md`, `transcribe.sh`,
future dependency manifest and environment-check instructions.

**Proposed commit:** `build: document and validate the supported runtime environment`

**Safe to automate:** local metadata collection and documentation; dependency
installation and runtime replacement should be a separately scoped task.

### 4. Harden the wrapper before rearranging the code

**Finding:** `transcribe.sh` uses `$1` and writes the source-audio sidecar before
WhisperX validates the invocation. It does not explicitly guard missing input,
failed environment activation, or a missing input file. Its own comments also
confirm that `--output_dir` can redirect WhisperX output while the sidecar stays
in the default archive. Review tooling looks for that sidecar beside its input.

**Steps:** add early argument/environment validation and make the sidecar follow
the effective output directory. Decide how source-path records should behave
when transcription fails or different audio files share a basename. Test with a
stub WhisperX executable and temporary directories so these checks require no
models, network, credentials, or private audio.

**Completion criteria:** no-argument, help, missing-file, missing-environment,
paths-with-spaces, and output-override cases have deliberate behavior; invalid
invocations do not create misleading archive records.

**Files:** `transcribe.sh`, `review_transcript.py` if lookup behavior changes,
new wrapper tests, `docs/installation.md` and README output documentation.

**Proposed commit:** `fix: validate transcription inputs and align source sidecars`

**Safe to automate:** implementation and isolated tests; changes to existing
archive records require separate review because they affect stored data.

### 5. Shorten the daily-use documentation and clarify local housekeeping

**Finding:** README is roughly 27 KB and overlaps the installation guide and
pipeline reference. The reference says tests cover four Python tools, while
there are now five tool-specific test modules. Local `scratch.md` contains
obsolete R commands and former in-repo output paths alongside recent logs.

**Steps:** keep README focused on purpose, a short workflow, output location,
and links. Put detailed flags and backend behavior in the reference, and setup
details in installation. Refresh the structure listing and test description.
Extract still-useful local scratch tasks into the new backlog using sanitized
descriptions; archive obsolete local commands without publishing personal paths
or raw transcript content. Inspect temporary scripts before deciding whether
they are superseded or deserve promotion; their names alone are not evidence
that they can be deleted.

**Files:** `README.md`, `docs/pipeline-reference.md`, `docs/installation.md`,
new `docs/README.md`; local-only `scratch.md`, `tmp_*.py`, `00_admin/`.

**Proposed commit:** `docs: streamline daily workflow and refresh repository index`

**Safe to automate:** tracked documentation edits; local deletion is not part
of the recommendation. Keep local drafts ignored unless deliberately reviewed.

### 6. Add lightweight maintenance entry points

**Steps:** add a `make test` target for the existing unittest command and shell
syntax check. Consider mocked wrapper coverage from step 4 and mocked backend
response tests where gaps remain. CI can follow if wanted, using synthetic
fixtures and no API keys or audio downloads. A repository-wide package move is
not needed to obtain these benefits; defer it until shared code or distribution
requirements justify the migration.

**Files:** `Makefile`, `tests/`, optionally a future CI configuration.

**Proposed commit:** `test: add a repeatable offline verification command`

**Safe to automate:** local targets and tests; enabling a hosted workflow is a
separate publishing decision.

## Suggested next session

The follow-up discussion prioritizes a public-benchmark comparison of the
installed Ollama models; see the plan below. Documentation organization,
wrapper fixes, and isolated dependency validation remain separate follow-ups.
For each completed item, record the evidence and outcome in a dated note,
update the active backlog, and keep the historical record intact.

## Follow-up — Ollama model update results

On 2026-10-04, the user supplied terminal output showing the installed models
before and after these commands:

```bash
ollama pull granite4.1:30b
ollama pull nemotron3:33b
ollama pull qwen3.6:35b
ollama list
```

All three pulls reported successful SHA-256 verification and manifest writing.
The resulting inventory was:

| Model tag | Previous ID | Resulting ID | Size before → after | Result |
| --- | --- | --- | --- | --- |
| `granite4.1:30b` | `3f3e5df8a021` | `3f3e5df8a021` | 17 GB → 17 GB | Unchanged |
| `nemotron3:33b` | `f6d8b7ff496c` | `f6d8b7ff496c` | 27 GB → 27 GB | Unchanged |
| `qwen3.6:35b` | `07d35212591f` | `a7eb95c53bcf` | 23 GB → 22 GB | Updated |

Granite and Nemotron already matched the published artifacts for those tags
at the time of the successful pulls. Qwen's artifact changed; its pull also
reported removal of unused layers. These results do not identify what changed
inside Qwen or establish a quality improvement. Sizes are the rounded values
reported by `ollama list`.

All three modification timestamps refreshed, including the two unchanged
models. Compare IDs, not modification times, when recording whether an artifact
changed. The model tags stayed the same; these commands do not establish an
Ollama application upgrade or the availability of newer model families.

**Next:** evaluate the installed candidates on the same transcripts and record
their IDs with the results, using `a7eb95c53bcf` as the Qwen evaluation baseline.
Then select and validate a default, update current-use documentation, and close
the WATERSHED decision. The repository's old Ollama fallback remains unchanged;
pulling these models alone does not repair it.

## Next-step plan — public benchmarks

**Status:** recommended plan; no datasets downloaded or benchmark runs completed.
Use public reference data instead of personal recordings. Keep the two stages
separate: WhisperX transcribes audio; the Ollama models receive text for
summarization and sanity checking in this repository.

### First: compare the Ollama models using QMSum

[QMSum](https://aclanthology.org/2021.naacl-main.472/) provides meeting
transcripts, queries, and reference summaries. It is a query-based summarization
benchmark, so use its questions explicitly rather than treating its references
as generic summaries for the repository's meeting presets.

1. Select and freeze a small development subset spanning shorter and longer
   meetings. Record the dataset revision, split, meeting/query IDs, and selection
   rule. Reserve separate examples for confirming the final choice.
2. Convert reference transcripts into the summarizer's text input format,
   preserving speaker labels and turn order. Retain the original reference data
   for scoring. Keep reference answers out of the model input.
3. Run the same transcript/query pairs through each installed model with
   `--engine ollama`, explicit `--model`, and `--type custom --prompt` carrying
   the query and identical instructions. Use single runs initially, without
   `--merge`, and keep outputs in separate model/run directories.
4. Compare factual accuracy, relevant information coverage, speaker attribution,
   unsupported claims, incomplete or blank responses, and elapsed time. Review
   against both the reference answer and source transcript; wording differences
   alone are not errors. Repeat promising candidates to assess variability.
5. Record exact model IDs, prompts, input length, hardware, Ollama version, and
   effective context/generation settings. Check that long inputs fit the actual
   configured context; advertised model capacity alone does not establish that.
   Report model-loading time separately from warm-run inference time.
6. Confirm the preferred candidate on the reserved examples and a small
   sanity-check evaluation before changing the shared default. QMSum reference
   text alone does not test detection of transcription errors: use ASR output
   paired with a reference transcript and manually score whether flags identify
   real errors. Record useful flags, false alarms, and missed errors; zero flags
   is not proof of correctness.
7. Document the choice and limitations, change the default and current-use
   examples together, and verify both tools without `--model`. Check environment
   and explicit model overrides, run the unit suite, and close the WATERSHED item.

Initial model IDs are Granite `3f3e5df8a021`, Nemotron `f6d8b7ff496c`, and
Qwen `a7eb95c53bcf`, from the user's October 4 results. Recheck IDs when running
the comparison. Keep benchmark audio and generated outputs outside the tracked
source tree; track the selection manifest, evaluation procedure, and compact
results summary. No new default has been selected.

### Second: benchmark the audio pipeline using AMI

Use a fixed subset of the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/download/)
for meeting transcription and speaker separation. Record the exact
[AMI partition](https://groups.inf.ed.ac.uk/ami/corpus/datasets.shtml), meeting
IDs, audio channel/microphone condition, and reference annotation version.
Tune on development data and reserve test data for final evaluation.

Measure these quantities separately:

| Measure | Meaning and reporting rule |
| --- | --- |
| Word error rate (WER) | Substitutions + deletions + insertions, divided by reference words; lower is better. Use identical text normalization and report corpus totals. |
| Real-time factor (RTF) | Processing seconds divided by audio seconds; lower is faster. A 0.25 RTF means 15 minutes to process one hour. State whether loading, alignment, and diarization are included. |
| Peak memory | Record the measurement method and whether it covers the full pipeline or one process. |
| Diarization error rate (DER) | Missed speech, false speech detections, and speaker confusion; record overlap handling and boundary tolerance. |

[JiWER](https://github.com/jitsi/jiwer) provides WER scoring, and
[pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) provides DER
evaluation. Use the same hardware, settings, and inputs for each comparison.
Separate cold-start timing from repeated warm runs. Call a small selected subset
a local regression benchmark, not a full published benchmark result.

Optional later additions are
[LibriSpeech test-clean/test-other](https://www.openslr.org/12) for a read-speech
baseline and [Earnings-22](https://arxiv.org/abs/2203.15591) for long recordings
and varied accents. Start with QMSum and AMI to keep the work focused on this
repository's meeting workflow.


## Follow-up — transcription startup troubleshooting

Added README navigation and installation troubleshooting for the user's
TorchCodec loader warning, Lightning checkpoint migration notice, and blank
`Transcript:` line. Corrected the installation guide's claim that unpinned
commands and the Python package snapshot reproduce the entire runtime exactly.

Read-only inspection confirmed WhisperX 3.8.6 decodes via the FFmpeg executable
and passes waveform dictionaries to pyannote VAD and diarization. Both FFmpeg
8.1.2_1 and ffmpeg@7 7.1.5_1 were installed. Importing TorchCodec's AudioDecoder
succeeded with `DYLD_LIBRARY_PATH=/opt/homebrew/opt/ffmpeg@7/lib` scoped to that
Python process. This verifies library loading only. No recording was processed,
checkpoint migrated, dependency installed, or shell configuration changed.
The supplied log does not establish whether the original run completed.

Initial proposed runtime check (subsequently attempted below): transcribe a short
known-speech sample into a separate
output directory with the scoped library path, then verify exit status, text,
word timestamps, and speaker labels. Full instructions and upstream references
are in [installation troubleshooting](installation.md#torchcodec-and-ffmpeg-on-macos).


## Follow-up — public speech test results and repair boundary

The user supplied two runs of the Open Speech Repository Harvard Sentences
sample, with `--min_speakers 1 --max_speakers 1`. Both produced recognizable
text, reached alignment and diarization, and returned exit status `0`.

- **15:44 run:** assigning `DYLD_LIBRARY_PATH` before `transcribe` left the
  original TorchCodec loader warning intact. A local shell-propagation check
  showed that the variable disappeared through `/bin/bash`.
- **15:48 run:** exporting the variable inside `/bin/bash` and sourcing
  `transcribe.sh` removed the TorchCodec warning. It introduced duplicate
  Objective-C class warnings for `AVFFrameReceiver` and `AVFAudioReceiver`,
  defined by both PyAV's bundled `libavdevice.62.1.100.dylib` and Homebrew
  FFmpeg 7's `libavdevice.61.3.100.dylib`.

Both logs retained the Lightning checkpoint migration notice and pyannote's
pooling `std()` warning. There was no crash, but the duplicate-library warning
prevents treating the scoped path workaround as a stable repair. The generated
JSON was not independently inspected; an attempted read at the expected path
found no file in the assistant's filesystem view. The original recording's
blank segment and multi-speaker accuracy remain unverified.

Updated the installation guide to replace the earlier wrapper workaround with
these findings and an isolated repair plan. Next: inventory PyAV and the other
package/native-library requirements, choose a compatible candidate environment,
then test combined imports, actual decoding, and the full public sample before
adoption. No candidate versions selected, environment created, dependencies
changed, libraries deleted, or wrapper modified during this documentation update.
See [the repair plan](installation.md#next-repair-step-isolate-and-validate-the-decoder-dependencies).
