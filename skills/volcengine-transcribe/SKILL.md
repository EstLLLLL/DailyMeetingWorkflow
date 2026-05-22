---
name: volcengine-transcribe
description: Transcribe a meeting recording with Fish Audio ASR (direct API), then polish and summarize with DeepSeek (direct API), and write an Obsidian-ready meeting memo. Use when the user wants speech-to-text written into Obsidian as a meeting memo with a detailed summary and a polished, readable transcript.
---

# Meeting Transcribe (Fish ASR + DeepSeek)

Transcribe a recording and turn it into an Obsidian meeting memo:

```
audio → Fish Audio /v1/asr (direct) → DeepSeek (direct) polish + summary → memo.md + result.json
```

- **ASR**: Fish Audio's own API — the single ASR path. No ElevenLabs-first fallback,
  and Fish is **not** routed through Doubao / Volcengine Ark.
- **Polish + summary**: DeepSeek's own API (`https://api.deepseek.com`), not via Ark.
- **Chunking**: files over Fish's ~22 MB limit are split with ffmpeg automatically.

> The skill folder is still named `volcengine-transcribe` for continuity; the active
> engine is Fish + DeepSeek. See `CLAUDE.md` for the project-level summary.

## Workflow
1. Before transcribing, unless the user already provided them, ask two short questions:
   - 参会人有哪些？
   - 关键词有哪些？
   Reuse any speaker mapping the user already gave instead of asking again.
2. Collect the local audio path, language (optional), and output directory.
3. Run `scripts/transcribe_fish.py`. It calls Fish ASR, chunking long files with
   ffmpeg, then runs DeepSeek to produce a polished transcript and a structured
   summary, and writes the memo + raw JSON.
4. Pass participants via `--participant`, focus terms via `--keyword`, and exact
   speaker mappings via `--speaker-alias` (or the `VOLCENGINE_SPEAKER_ALIASES` env).
5. Review speaker labels before reporting success. Fish has no diarization, so labels
   are DeepSeek's best-effort inference — say so rather than asserting certainty.

## Decision Rules
- Fish ASR returns timestamped segments but **no speaker labels**. DeepSeek infers
  speakers during polishing from context. With no reliable mapping, keep generic
  labels; do not invent real names.
- Participant names and keywords are hints only. Do not force a name onto an
  ambiguous line.
- For polished transcripts, keep the conversational/Q&A flow; merge only fragmented
  or repetitive phrasing. Do not collapse multiple rounds into a short summary.
- Keep `--language` unset unless known. For Mandarin-only audio, `zh` is a safe choice.
- Long audio is chunked at ~240s (or smaller when a chunk would exceed ~22 MB).
  Chunk results are cached in a `.fish-chunks-*` sibling dir, so an interrupted run
  resumes without re-transcribing completed chunks.
- Voice Memos `.qta` files must be converted to `.m4a` before transcription.
- Memo output preferences: keep `Date` and `Original file`; a detailed summary
  (Discussion vs Interview framework, chosen automatically); a polished, readable
  transcript; replace generic speaker labels with names only when a mapping is given.

## Environment
```bash
export FISH_API_KEY="your-fish-key"            # or FISH_AUDIO_API_KEY
export DEEPSEEK_API_KEY="your-deepseek-key"
export DEEPSEEK_MODEL="deepseek-chat"          # optional, default deepseek-chat
export DEEPSEEK_BASE_URL="https://api.deepseek.com"   # optional
export MEETING_MEMO_DIR="$HOME/path/to/your/Obsidian/meeting memo"  # output dir
export VOLCENGINE_SPEAKER_ALIASES="1=Joe;2=投资方"     # optional default speaker map
```
Requires `python3` (stdlib only), `ffmpeg`/`ffprobe`, and `curl`.

## CLI
```bash
python3 skills/volcengine-transcribe/scripts/transcribe_fish.py \
  ./meeting.m4a \
  --language zh \
  --participant "Joe,投资方,法务" \
  --keyword "商业模式,定价,竞争格局" \
  --speaker-alias "1=Joe" \
  --out-dir "$MEETING_MEMO_DIR"
```
Skip the DeepSeek stage and keep only the raw timestamped transcript:
```bash
python3 skills/volcengine-transcribe/scripts/transcribe_fish.py ./meeting.m4a --skip-polish
```

## Output Conventions
- `<YYYY-MM-DD>-<name>_meeting-memo.md` — Obsidian memo: `Date`, `Original file`,
  `## Summary`, `## Polished Transcript`.
- `<YYYY-MM-DD>-<name>_result.json` — raw ASR response.
- Timestamps in `HH:MM:SS.mmm`.
- Output dir resolves from `--out-dir`, then `$MEETING_MEMO_DIR`, then the legacy
  `$VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR`, then a personal default (change it).

## Reference Map
- `scripts/transcribe_fish.py`: the transcription script — Fish ASR (direct,
  ffmpeg-chunked) + DeepSeek (direct) polish/summary → Obsidian memo.
- `scripts/keyterms.example.txt`: template for a personal terminology list. Copy it
  to `keyterms.txt` (gitignored), fill in your own terms, and pass `--keyterms-file`.
