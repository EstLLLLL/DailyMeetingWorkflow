# Meeting Memo Transcribe Skill

This project defines the `/transcribe` Claude Code slash command for audio transcription.

## Slash Command
`~/.claude/commands/transcribe.md` — invoke with `/transcribe <audio-file-path>`

## Pipeline
1. **ASR — Fish Audio, direct API** (`POST https://api.fish.audio/v1/asr`). This is
   the single ASR path: no ElevenLabs-first fallback, and Fish is called through its
   own API, not via Doubao / Volcengine Ark. Fish returns timestamped segments but
   no speaker diarization, so speaker attribution is best-effort.
2. **Polish + summary — DeepSeek, direct API** (`https://api.deepseek.com`). Not via
   Ark/Doubao. Produces a polished Q&A transcript and a Chinese summary.
3. **Output** — write `result.json`, `transcript.srt`, and an Obsidian meeting memo.

## Underlying Scripts
- `scripts/transcribe_fish.py` — Fish ASR (direct) + DeepSeek (direct) → memo.
- `scripts/keyterms.example.txt` — template for a personal terminology list. Copy to
  `keyterms.txt` (gitignored), fill in your own terms, pass via `--keyterms-file`.

## Output Directory
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/Raw/meeting memo/`
(override with `$MEETING_MEMO_DIR` or `--out-dir`).

## Required Environment Variables

```
FISH_API_KEY                # Fish Audio ASR (fish.audio/app/api-keys)
DEEPSEEK_API_KEY            # DeepSeek (polishing + summary)
DEEPSEEK_MODEL              # default: deepseek-chat
DEEPSEEK_BASE_URL           # default: https://api.deepseek.com
```

Optional:

```
MEETING_MEMO_DIR                      # output dir (preferred; falls back to the legacy var below)
VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR  # legacy output-dir override
VOLCENGINE_SPEAKER_ALIASES            # default speaker map, e.g. "1=Joe;2=Bob"
```
