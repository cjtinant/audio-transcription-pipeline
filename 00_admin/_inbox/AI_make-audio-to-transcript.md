
# Transcripts from a Zoom Meeting
If you're the host:

Record the meeting (locally or to the cloud) — Zoom can save a separate audio
file (M4A format) alongside the video.

In recording settings, enable "Record a separate audio file for each participant"
 or just use the default which saves an audio track.

After the meeting, the local recording folder will contain an audio_only.m4a file.

Third-party options:

Use audio recording software (like Audacity or even QuickTime on Mac) to capture
 your system audio during the meeting.
On Mac, tools like BlackHole or Loopback let you route and record system audio
 cleanly.
On Windows, you can use the built-in Stereo Mix feature or apps like VB-Cable.

After the fact (from a video file):
If you already have a Zoom recording video file (.mp4), you can extract the audio using a free tool like VLC (Media → Convert/Save → select audio-only output) or ffmpeg:
ffmpeg -i zoom_recording.mp4 -vn -acodec copy output.m4a

The easiest route by far is just enabling the audio-only recording in Zoom's settings before the meeting starts.

## Extract
Whisper (OpenAI) — the gold standard for free transcription. You run it locally
via Python or a GUI wrapper. Very accurate, supports many languages. A bit
technical to set up but worth it.
Whisper GUI wrappers — if you don't want to use the command line, apps like
Whisperfile, MacWhisper (Mac), or **Whisper Transcription** make it point-and-click.

Built into tools you may already have

Word / Microsoft 365 — has a transcribe feature under Dictate that accepts
 uploaded audio files. Google Docs — voice typing works live, but doesn't
  directly accept audio files without routing through your speakers.
Zoom's own AI Companion — if your plan includes it,
Zoom can auto-transcribe cloud recordings for you.

My suggestion: If you want simple and free, MacWhisper (Mac) or Whisperfile is the easiest path. If you're okay with a little setup, local Whisper gives you the best accuracy with no cost or data privacy concerns — good if the meeting content is sensitive.

## Whisper Transcription
For your use case (Zoom meeting audio), I'd recommend:

Start with the "Small" (WhisperKit, 483 MB) — it's already highlighted as
recommended, runs fast on Mac, and includes Speaker Recognition which is really
valuable for meeting transcriptions so you can tell who said what.
If accuracy isn't quite good enough after trying Small, step up to a WhisperKit
Medium or Large model for better results, at the cost of more RAM and slower processing.

Speaker Recognition is the key feature for meetings — I'd prioritize any model
that includes it (the Small recommended one does, note the speaker icon next to it).

You already have Whisper Transcription installed (the blue microphone icon, top left — it shows "Open"). That's actually the one I'd recommend from this list! It has 978 reviews at 4 stars, and it's the app we were just looking at in your previous screenshot with the WhisperKit models and speaker recognition.
Stick with what you've got — no need to download anything else.

For transcription purposes, audio only is better (or at least equal). Here's why:

Transcription models like Whisper only process the audio track anyway — the video data is ignored entirely.
A .m4a audio file is much smaller than the .mp4 video, so it'll load and process faster.
Less chance of any file handling issues.

So the ideal workflow for your Zoom call would be:

Get the Zoom recording (.mp4 or .m4a)
If you only have the .mp4, either use it directly (Whisper Transcription should accept it) or extract the audio first with something like VLC or ffmpeg
Drop it into Whisper Transcription, use the Small WhisperKit model with Speaker Recognition
Export the transcript to text
Drop it into your meeting notes .md template

If Zoom saved a separate audio_only.m4a alongside the video in your recordings folder, use that — it's the most efficient option.

Yes, keep the timestamps when pulling key themes. Here's why it helps:

If you're using Claude (or any AI) to extract themes, the timestamps give you traceability — you can go back to the exact moment in the recording to verify context.
Segmented text helps the AI understand where topic shifts happen, which improves theme detection.
It makes it easier to attribute which part of the meeting a theme came from (early discussion vs. decisions at the end, etc.).

Without speaker recognition, timestamps partially compensate — you can at least say "around the 14-minute mark the conversation shifted to X" even if you don't know who said it.
Suggested prompt to use with the transcript:

"Here is a timestamped transcript of a Zoom meeting. Please identify the key themes discussed, summarize each one briefly, and note the approximate timestamp where each theme was most prominent."

Then paste the transcript in. That'll give you a solid structured output you can drop into your notes template.
One tip: if the transcript is long, you may want to paste it in chunks (e.g., every 30 minutes of meeting) to stay within context limits and get more focused theme extraction per segment.

Here is a timestamped transcript of a Zoom meeting. Please identify the key themes discussed, summarize each one briefly, and note the approximate timestamp where each theme was most prominent
