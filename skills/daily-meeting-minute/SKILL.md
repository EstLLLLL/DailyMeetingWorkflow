---
name: daily-meeting-minute
description: Daily routine that picks the newest recording from the iCloud Recordings folder and turns it into an Obsidian meeting memo via the volcengine-transcribe skill. Use when the user says "do today's meeting minute", "整理今天的会议录音", or otherwise wants the latest recording processed into the meeting memo folder.
---

# Daily Meeting Minute

The daily routine: take the most recently updated recording from the iCloud
`Recordings` folder and process it into the Obsidian `meeting memo` folder, using
the `volcengine-transcribe` skill for transcription and memo generation.

## Folders
- Recordings (input): `~/Library/Mobile Documents/com~apple~CloudDocs/Recordings`
  - Override with `MEETING_RECORDINGS_DIR`.
- Meeting memo (output): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/meeting memo`
  - Same as `VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR` in `volcengine-transcribe`.

## Workflow
1. Find the newest recording. Default to the single most recent file:
   ```bash
   bash scripts/find_latest_recording.sh --latest
   ```
   To review what is new today before picking, run:
   ```bash
   bash scripts/find_latest_recording.sh --today
   ```
2. Show the user the file you picked (name + modified time) and confirm it is the
   recording they mean before transcribing. If several recordings were added the
   same day, list them and ask which one(s) to process.
3. Ask the two standard questions from `volcengine-transcribe` unless already given:
   - 参会人有哪些？
   - 关键词有哪些？
4. Hand the chosen file to the `volcengine-transcribe` skill, writing into the
   meeting memo folder. For a normal-length recording:
   ```bash
   python3 "$VOLCENGINE_TRANSCRIBE_CLI" \
     "<latest-recording-path>" \
     --language zh-CN \
     --participant "<participants>" \
     --keyword "<keywords>" \
     --out-dir "$VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR"
   ```
   For a long recording (over the flash limits), use the chunked CLI
   (`VOLCENGINE_TRANSCRIBE_FULL_CLI`) instead, per the `volcengine-transcribe` skill.
5. Confirm the memo landed in the meeting memo folder and report the file name.

## Decision Rules
- "Newest recording" means most recently modified audio file under the Recordings
  folder, ignoring hidden support files like `.CloudRecordings_SUPPORT`.
- If a file is a Voice Memos `.qta`, let `volcengine-transcribe` handle the
  `.qta` → `.m4a` conversion; do not pre-convert here.
- Never transcribe silently. Always confirm the picked file with the user first,
  since "today's recording" can be ambiguous when multiple were synced.
- Defer all transcription, speaker-labeling, and memo-formatting behavior to the
  `volcengine-transcribe` skill. This skill only handles "which file" and "kick
  off the routine".
- If no audio files are found in the Recordings folder, say so plainly instead of
  guessing a path.

## Reference Map
- `scripts/find_latest_recording.sh`: list newest recordings, or print only the
  latest (`--latest`) or only today's (`--today`).
- Depends on the `volcengine-transcribe` skill for the actual transcription and
  Obsidian memo output.
