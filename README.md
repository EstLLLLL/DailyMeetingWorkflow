# Daily Meeting Workflow

会议工作流相关的 Claude/Codex skills 集合，覆盖从录音转录到 Obsidian 笔记整理的环节。

## Skills

| Skill | 作用 |
|---|---|
| [`volcengine-transcribe`](skills/volcengine-transcribe/SKILL.md) | 用 Volcengine Doubao Speech 或 ElevenLabs 转录录音，再经 Ark 生成 Obsidian meeting memo（详细摘要 + Q&A 风格转录）。 |
| [`interview-summary`](skills/interview-summary/SKILL.md) | 按主持人核心问题的顺序，对访谈/播客/Q&A 做结构化、可复盘的高质量摘要。 |
| [`bilingual-interview`](skills/bilingual-interview/SKILL.md) | 把英文访谈转录整理成中英对照的 Markdown，便于在 Obsidian 中阅读。 |

## 目标工作流（建设中）

完整的 daily / weekly 流程目标如下，部分环节尚未落库：

1. **抓取当天新录音** —— 从 iCloud 文件夹拉取当天新增录音（待补 skill / 脚本）。
2. **转录** —— `volcengine-transcribe`。
3. **更新 Obsidian dashboard** —— 把 memo 汇总到 dashboard（目前只写单条 memo，dashboard 汇总待补）。
4. **Weekly meeting review** —— 每周对会议做回顾（待补 skill）。

## 待补充

- `volcengine-transcribe` 引用的脚本尚未入库：`scripts/transcribe_volcengine.py`、`scripts/transcribe_volcengine_full.py`、`scripts/audio_duration.swift`、`scripts/audio_range_export.swift`、`references/api.md`。
- 抓取 iCloud 录音、Obsidian dashboard 汇总、weekly review 三个环节的 skill / 脚本。
