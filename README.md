# Daily Meeting Workflow

会议工作流相关的 Claude/Codex skills 集合，覆盖从录音转录到 Obsidian 笔记整理的环节。

## Skills

| Skill | 作用 |
|---|---|
| [`daily-meeting-minute`](skills/daily-meeting-minute/SKILL.md) | 每日例行：从 iCloud `Recordings` 文件夹挑出最新录音，交给 `volcengine-transcribe` 整理成 meeting memo。 |
| [`volcengine-transcribe`](skills/volcengine-transcribe/SKILL.md) | 用 Volcengine Doubao Speech 或 ElevenLabs 转录录音，再经 Ark 生成 Obsidian meeting memo（详细摘要 + Q&A 风格转录）。 |
| [`meeting-dashboard`](skills/meeting-dashboard/SKILL.md) | 把 meeting memo 文件夹里的所有 memo 汇总成一个 Obsidian dashboard 索引笔记（草稿）。 |
| [`weekly-meeting-review`](skills/weekly-meeting-review/SKILL.md) | 每周跨会议综述本周 memo：重点主题、关键决定、行动项、待跟进（草稿）。 |
| [`interview-summary`](skills/interview-summary/SKILL.md) | 按主持人核心问题的顺序，对访谈/播客/Q&A 做结构化、可复盘的高质量摘要。 |
| [`bilingual-interview`](skills/bilingual-interview/SKILL.md) | 把英文访谈转录整理成中英对照的 Markdown，便于在 Obsidian 中阅读。 |

## 工作流

1. **抓取当天新录音 + 转录** —— `daily-meeting-minute`：从 iCloud `Recordings` 挑最新录音，调用 `volcengine-transcribe` 写进 meeting memo。
2. **更新 Obsidian dashboard** —— `meeting-dashboard`：把 memo 汇总成索引笔记。
3. **Weekly meeting review** —— `weekly-meeting-review`：每周跨会议综述。

## 待补充

- `volcengine-transcribe` 引用的脚本尚未入库：`scripts/transcribe_volcengine.py`、`scripts/transcribe_volcengine_full.py`、`scripts/audio_duration.swift`、`scripts/audio_range_export.swift`、`references/api.md`。
- `meeting-dashboard` 与 `weekly-meeting-review` 目前是草稿，dashboard 的格式/位置、weekly review 的文件夹命名等细节待按本人习惯确认。
