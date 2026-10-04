# Reviewing transcript accuracy

A zero exit status verifies process completion; populated JSON verifies output
structure. Neither proves the transcript matches the recording. Keep the raw
JSON as the original record and save corrections in a separate text export.
All review outputs and clips belong in the private audio-transcription-output
folder, not this source repository.

## 1. Open the review and generate a confidence report

For recording 7, run:

```bash
cd ~/PROJECTS/audio-transcription-pipeline
transcript="$HOME/PROJECTS/audio-transcription-output/2026-10-04_recording-7.json"
.venv/bin/python review_transcript.py "$transcript" --report
```

This opens the HTML review and writes a `_flagged.txt` report beside the
transcript. For recording 8, change the filename to
`2026-10-04_recording-8.json`. Use `--no-open` to generate files without opening
the browser. The original JSON is not modified.

The report flags words with scores below 0.2 by default. To flag more words,
raise the threshold, for example `--report --threshold 0.4`. Scores prioritize
listening; they are not calibrated correctness probabilities. High-scoring
words can be wrong, and missing speech cannot be found just by flagging words
that were recognized. Words without scores are skipped by the report. The
report threshold and the HTML slider are separate controls.

## 2. Compare against the audio

Start by listening to the beginning, several middle passages, and the end.
Confirm the opening/closing speech is represented and that timestamps track
the source. Listen across conspicuous gaps: silence or a thinking pause may be
legitimate, while audible omitted speech needs correction. The first word need
not start at zero and the final word need not reach the file's exact duration.

Prioritize names, acronyms, technical terms, numbers, dates, units, negations,
and statements used for decisions or action items. Check repeated phrases,
unexpected capitalization, and awkward wording against the audio rather than
rewriting them from context. Include some unflagged passages in the review.

For a clip around a report timestamp, substitute the time you want to hear:

```bash
.venv/bin/python review_transcript.py "$transcript" \
  --clip 02:15 --clip-padding 5
```

This writes and opens a WAV covering up to five seconds on either side. It
requires a matching entry in `.source-audio.json` beside the JSON and the
original audio still at that path. If that lookup fails, open the source audio
manually and seek to the timestamp; no retranscription is required just to
listen. Repeating the same clip timestamp replaces that generated clip.

Spot checks are a practical first pass, not full verification. For a transcript
that must be accurate throughout, listen to the entire recording while following
the text. Record whether review was complete or sampled, and any unresolved
intervals.

## 3. Check speaker attribution

For a solo recording, a single consistent label is expected. For multiple
speakers, listen at turn boundaries and check for merged voices or one voice
split across labels. Assign names only when you can identify the voice. Merely
mentioning someone's name does not make that person the speaker.

The HTML review supports speaker naming and labeled-text export. Browser name
changes do not modify the raw JSON. If later tools need persistent speaker names,
use `review_transcript.py --save-speakers` with confirmed label/name pairs
(for example `--save-speakers "SPEAKER_00=Confirmed Name"`). This writes a
speaker cache for downstream tools; it does not rewrite the raw transcript.

## 4. Save a corrected derivative

Export labeled text from the review, then correct that text against the audio.
Save it alongside the raw JSON, for example
`2026-10-04_recording-7_clean.txt`. Preserve meaning and speaker attribution;
do not fill gaps with guesses. Mark unresolved passages with a timestamp, such
as `[unclear at 02:15]`, for later review.

Before using the result for a summary, verify consequential names, numbers,
negations, and action items. Use the corrected text as the summarizer input.
Keep a short private note of the review date, full-versus-sampled coverage, and
remaining uncertainties. Optional LLM checks are not a replacement for audio
comparison and are not required for this local review workflow.
