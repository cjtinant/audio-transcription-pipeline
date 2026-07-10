# Connecting a local folder in Cowork

By default, Cowork only sees files you explicitly upload, and can't write
changes back to them — edits land in a temporary copy that you have to download
and move into place yourself (this is what happened with the
`audio-transcription-pipeline` README).

Connecting a folder fixes that: Claude gets direct read/write access to the real
files on disk, in place, for the rest of the session.

## Steps

1. Ask Claude to connect the folder — e.g. "connect
   `~/PROJECTS/audio-transcription-pipeline`" — or just ask it to work on files
   in a project; it will offer to request access.
2. If you gave a path, Claude requests that exact folder and you approve it. If
   no path is given, a native folder picker opens (local sessions only) and you
   choose the folder yourself.
3. Once approved, the folder is mounted for the session. Claude can read, edit,
   and create files there directly — no upload/download round-trip.
4. Access is scoped to that session. To work in a different project folder
   later, repeat the request with the new path.

## Notes

- No GitHub connector is available in Cowork's connector registry as of 2026-07
  — folder connection is the way to get direct file access for a Git repo.
  Committing/pushing still happens through your normal Git workflow (terminal,
  GitHub Desktop, etc.), not through Cowork.
- Works the same for any project — not specific to this pipeline.
- If you only want Claude to read reference material without editing anything,
  uploading individual files (as done for README.md and WATERSHED.md in this
  session) is still fine — folder connection is for when you want direct edits.
