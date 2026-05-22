# Meeting Memo Transcribe Skill

This project defines the `/transcribe` Claude Code slash command for audio transcription.

## Slash Command
`~/.claude/commands/transcribe.md` — invoke with `/transcribe <audio-file-path>`

## ASR Provider (current direction)
ASR uses **Fish Audio directly via its own API** — the single ASR path. Do not run
ElevenLabs first with a Fish fallback, and do not route Fish through Doubao /
Volcengine Ark. Call Fish Audio's native speech-to-text API.

> TODO: implement the Fish-direct ASR path. Needs the Fish Audio ASR API details
> (endpoint, auth/`FISH_API_KEY`, model). The scripts below predate this decision.

## Underlying Scripts
All scripts live in `~/.codex/skills/volcengine-transcribe/scripts/`:

- `transcribe_elevenlabs.py` — (to be replaced) ElevenLabs Scribe v2 ASR + Claude Sonnet polishing
- `keyterms.txt` — Domain-specific terms for better ASR recognition (edit as needed)
- `transcribe_volcengine.py` — Legacy: Volcengine Doubao flash API
- `transcribe_volcengine_full.py` — Legacy: Chunked transcription for large files

## Output Directory
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/Meeting Memo/`

## Required Environment Variables

```
ELEVENLABS_API_KEY          # ElevenLabs Scribe ASR
ARK_API_KEY                 # DeepSeek V3 via Volcengine Ark (polishing + summary)
ARK_MODEL                   # e.g. deepseek-v3-2-251201
ARK_BASE_URL                # https://ark.cn-beijing.volces.com/api/v3
```

Optional:

```
VOLCENGINE_SPEAKER_ALIASES  # Default speaker mappings (e.g. "1=Joe;2=Bob")
```
