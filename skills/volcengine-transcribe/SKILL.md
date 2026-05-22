---
name: volcengine-transcribe
description: Transcribe recordings with Volcengine Doubao Speech or ElevenLabs Speech-to-Text, then export Obsidian-ready meeting notes with detailed summaries plus polished Q&A-style transcripts. Use when the user wants speech-to-text written into Obsidian as a meeting memo instead of plain transcript files.
---

# Volcengine Transcribe

Transcribe recordings with a speech provider selected through environment variables. The bundled CLI now supports:

- `TRANSCRIBE_PROVIDER=volcengine`: Volcengine Doubao Speech
- `TRANSCRIBE_PROVIDER=elevenlabs`: ElevenLabs Speech-to-Text

Ark is still used for the second stage:

- polished Q&A-style transcript
- structured summary / meeting memo

## Workflow
1. Before any transcription run, first ask the user two short questions:
   - 参会人有哪些？
   - 关键词有哪些？
   If the user already provided speaker mapping, reuse it instead of asking again.
2. Collect the input audio path or audio URL, desired language, and output directory.
3. If `TRANSCRIBE_PROVIDER=volcengine`, prefer `VOLCENGINE_SPEECH_API_KEY` for speech authentication. If it is unavailable, fall back to `VOLCENGINE_SPEECH_APP_ID` plus `VOLCENGINE_SPEECH_ACCESS_TOKEN`.
4. If `TRANSCRIBE_PROVIDER=elevenlabs`, use `ELEVENLABS_API_KEY` and `ELEVENLABS_STT_MODEL` for speech-to-text. Do not ask the user to paste secrets into chat.
5. Pass user-provided participants through `--participant` and focused topics through `--keyword`. Pass exact speaker mappings through `--speaker-alias`.
6. Use the bundled CLI to choose the provider flow automatically, then save raw JSON, subtitle output, and an Obsidian-ready Markdown meeting memo.
7. Review the transcript for speaker labels and timestamps before reporting success.
8. Run the transcript through Doubao text generation to produce:
   - a polished Q&A-style transcript that keeps the original conversation order
   - a detailed summary focused on each participant's main viewpoints
9. If the API returns transcript text but no speaker labels, state that explicitly instead of inventing speakers.
10. For larger local recordings, use the bundled chunked CLI instead of direct flash upload or one-shot upload.
11. If the input is a Voice Memos `.qta` file, convert it to `.m4a` first and then continue the normal transcription flow automatically.

## Decision Rules
- If `TRANSCRIBE_PROVIDER=volcengine`, default to the flash API for local files with resource ID `volc.bigasr.auc_turbo`.
- If `TRANSCRIBE_PROVIDER=volcengine`, default to the standard async API for remote URLs with resource ID `volc.seedasr.auc`.
- If `TRANSCRIBE_PROVIDER=elevenlabs`, default to `ELEVENLABS_STT_MODEL=scribe_v2` and prefer diarization enabled.
- Prefer the flash API for Volcengine local files because the official docs explicitly support `audio.data` base64 uploads and still return `utterances` with timestamps.
- Prefer ElevenLabs when the user wants to swap only the speech provider while keeping Ark for memo generation.
- Use Doubao via Ark Chat Completions after transcription to polish transcript wording and draft the meeting summary.
- Always ask for participants and keywords before running unless the user already supplied them in the same request.
- If the user provides only a participant list and not an exact speaker mapping, use those names as labeling hints in the memo, but do not force a wrong match when the transcript is ambiguous.
- For polished transcripts, keep the Q&A flow and merge only fragmented or repetitive phrasing. Do not collapse multiple question-answer rounds into a short summary.
- Treat speaker labels as best-effort output from the API. If the response lacks a recognizable speaker field, keep the transcript timestamped and label the line as `Speaker ?`.
- Use local files directly when they are within the flash API limits: no more than 2 hours and no more than 100 MB.
- Treat Voice Memos `.qta` files as a pre-processing case: export them to `.m4a` automatically before upload or chunking.
- Keep `language` unset unless the user knows the audio language. For Mandarin-only audio, `zh-CN` is a safe explicit choice.
- Prefer these output preferences when writing the memo:
  - no top-level title
  - keep `Date` and `Original file`
  - keep the summary direct and light on boilerplate
  - keep the transcript in readable Q&A style, not word-by-word
  - do not guess real names by default
- only replace generic labels with natural names or roles when the user explicitly provides the mapping
- if the user gives only participant names, use them as memo hints and keyword focus, not as guaranteed raw diarization labels

## Environment
Set these once in the shell:

```bash
export TRANSCRIBE_PROVIDER="volcengine"
export VOLCENGINE_SPEECH_APP_ID="your-app-id"
export VOLCENGINE_SPEECH_ACCESS_TOKEN="your-access-token"
export VOLCENGINE_SPEECH_API_KEY="your-speech-api-key"
export VOLCENGINE_SPEECH_RESOURCE_ID="volc.seedasr.auc"
export VOLCENGINE_SPEECH_FLASH_RESOURCE_ID="volc.bigasr.auc_turbo"
export ELEVENLABS_API_KEY="your-elevenlabs-api-key"
export ELEVENLABS_BASE_URL="https://api.elevenlabs.io"
export ELEVENLABS_STT_MODEL="scribe_v2"
export ELEVENLABS_LANGUAGE_CODE="zh"
export ELEVENLABS_DIARIZE="true"
export ELEVENLABS_NUM_SPEAKERS=""
export ELEVENLABS_NO_VERBATIM="true"
export VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/meeting memo"
export VOLCENGINE_SPEAKER_ALIASES="1=Joe;2=投资方;3=投资方;4=投资方同事"
export VOLCENGINE_MEETING_PARTICIPANTS="Joe,投资方,法务"
export VOLCENGINE_MEETING_KEYWORDS="商业模式,定价,竞争格局"
export ARK_API_KEY="your-ark-api-key"
export ARK_MODEL="your-endpoint-id-or-model-id"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
```

## CLI Path

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export VOLCENGINE_TRANSCRIBE_CLI="$CODEX_HOME/skills/volcengine-transcribe/scripts/transcribe_volcengine.py"
export VOLCENGINE_TRANSCRIBE_FULL_CLI="$CODEX_HOME/skills/volcengine-transcribe/scripts/transcribe_volcengine_full.py"
```

## CLI Quick Start
Basic timestamped diarization from a local file:

```bash
python3 "$VOLCENGINE_TRANSCRIBE_CLI" \
  ./meeting.mp3 \
  --language zh-CN \
  --out-dir "$VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR"
```

Switch only the speech provider to ElevenLabs while keeping Ark as the LLM layer:

```bash
export TRANSCRIBE_PROVIDER="elevenlabs"
export ELEVENLABS_API_KEY="your-elevenlabs-api-key"
export ELEVENLABS_STT_MODEL="scribe_v2"

python3 "$VOLCENGINE_TRANSCRIBE_CLI" \
  ./meeting.mp3 \
  --language zh \
  --out-dir "$VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR"
```

Large local recording with automatic chunking and merged output:

```bash
python3 "$VOLCENGINE_TRANSCRIBE_FULL_CLI" \
  ./long-meeting.m4a \
  --language zh-CN \
  --chunk-seconds 300 \
  --speaker-alias "1=Joe" \
  --participant "Joe,投资方,法务" \
  --keyword "商业模式,竞争格局,风险" \
  --out-dir "$VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR"
```

If you use the newer speech API key flow, only this speech credential is required:

```bash
export VOLCENGINE_SPEECH_API_KEY="your-speech-api-key"
```

Remote URL with explicit async mode:

```bash
python3 "$VOLCENGINE_TRANSCRIBE_CLI" \
  "https://example.com/interview.wav" \
  --mode standard \
  --resource-id volc.seedasr.auc \
  --poll-interval 3 \
  --out-dir output/interview
```

## Output Conventions
- Save raw API output to `result.json`.
- Save an Obsidian meeting memo to Markdown.
- Save subtitle-style output to `transcript.srt`.
- Keep timestamps in `HH:MM:SS.mmm`.
- Prefix every generated filename with a timestamp so Obsidian notes do not collide.
- Prefer writing into `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/meeting memo`.
- Build the Obsidian note with:
  - date
  - original filename
  - detailed summary of main viewpoints by participant
  - polished Q&A-style transcript
  - no top-level title
  - explicit speaker aliases only when the user provided them
  - participant list and keywords treated as memo guidance when exact mapping is unavailable

## Reference Map
- `scripts/transcribe_volcengine.py`: direct speech-to-memo flow for normal files.
- `scripts/transcribe_volcengine_full.py`: chunk large local recordings, merge results, then generate one final memo.
- `scripts/audio_duration.swift`: read local audio duration for chunk planning.
- `scripts/audio_range_export.swift`: export a local audio slice for chunked runs.
- `references/api.md`: official API endpoints, Ark base URL notes, required headers, local-file upload notes, and relevant parameter notes from Volcengine docs.

For Mac Voice Memos inputs, both `.m4a` and `.qta` are supported. `.qta` files should be auto-converted to `.m4a` before transcription so the rest of the workflow stays unchanged.
