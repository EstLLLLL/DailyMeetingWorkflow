# Daily Meeting Workflow

一套会议工作流的 Claude/Codex skills：从录音文件夹抓取当天最新录音 → 转录 → 生成 Obsidian
meeting memo → 汇总 dashboard → 每周跨会议综述。

> 仓库面向「想复用类似方案」的人。所有个人路径都可以通过环境变量或参数覆盖，见下方
> [配置](#配置setup) 与 [注意事项](#注意事项)。

## Skills

| Skill | 作用 |
|---|---|
| [`daily-meeting-minute`](skills/daily-meeting-minute/SKILL.md) | 每日例行：从录音文件夹挑出最新录音，交给转录脚本生成 meeting memo。 |
| [`volcengine-transcribe`](skills/volcengine-transcribe/SKILL.md) | 转录：**Fish Audio ASR 直连** + **DeepSeek 直连** 润色/总结，生成 Obsidian meeting memo。 |
| [`meeting-dashboard`](skills/meeting-dashboard/SKILL.md) | 把 meeting memo 文件夹里的所有 memo 汇总成一个 Obsidian dashboard 索引笔记（草稿）。 |
| [`weekly-meeting-review`](skills/weekly-meeting-review/SKILL.md) | 每周跨会议综述本周 memo：重点主题、关键决定、行动项、待跟进。 |
| [`interview-summary`](skills/interview-summary/SKILL.md) | 按主持人核心问题顺序，对访谈/播客/Q&A 做结构化、可复盘的摘要。 |
| [`bilingual-interview`](skills/bilingual-interview/SKILL.md) | 把英文访谈转录整理成中英对照的 Markdown。 |

## 工作流

1. **抓取当天新录音 + 转录** —— `daily-meeting-minute` → `transcribe_fish.py`。
2. **更新 Obsidian dashboard** —— `meeting-dashboard`。
3. **Weekly meeting review** —— `weekly-meeting-review`。

## 转录管线（transcribe_fish.py）

```
录音 → Fish Audio /v1/asr（直连，>22MB 用 ffmpeg 分块）→ DeepSeek 润色 + 中文总结 → Obsidian memo
```

- **ASR**：Fish Audio 自有 API，单一路径（不走 ElevenLabs，也不经豆包/Volcengine Ark）。
- **润色 + 总结**：DeepSeek 自有 API 直连（`https://api.deepseek.com`）。
- **输出**：`<date>-<名字>_meeting-memo.md` + `<date>-<名字>_result.json`。

## 配置（Setup）

### 依赖
- `python3`（仅用标准库）
- `ffmpeg` / `ffprobe`（长音频分块、读时长）
- `curl`（调用 DeepSeek）

### 环境变量
```bash
export FISH_API_KEY="your-fish-key"          # 或 FISH_AUDIO_API_KEY
export DEEPSEEK_API_KEY="your-deepseek-key"
export DEEPSEEK_MODEL="deepseek-chat"        # 可选，默认 deepseek-chat
export DEEPSEEK_BASE_URL="https://api.deepseek.com"  # 可选

# 输出目录（务必改成你自己的，否则用内置个人默认路径）
export MEETING_MEMO_DIR="$HOME/path/to/your/Obsidian/meeting memo"
# 录音来源目录（daily-meeting-minute 用）
export MEETING_RECORDINGS_DIR="$HOME/path/to/your/Recordings"

# 可选：默认说话人映射
export VOLCENGINE_SPEAKER_ALIASES="1=Alice;2=Bob"
```

### 运行
```bash
# 单文件转录
python3 skills/volcengine-transcribe/scripts/transcribe_fish.py \
  ./meeting.m4a --language zh \
  --participant "Alice,Bob" --keyword "定价,竞争" \
  --out-dir "$MEETING_MEMO_DIR"

# 每日：挑出今天最新录音的路径
bash skills/daily-meeting-minute/scripts/find_latest_recording.sh --latest
```

## 注意事项

- **个人路径需替换**：仓库默认路径指向作者的 Obsidian vault（`Esther Workspace/Raw/meeting memo`
  等）。复用前用 `MEETING_MEMO_DIR` / `MEETING_RECORDINGS_DIR` / `--out-dir` 覆盖。
- **Fish ASR 无说话人分离**：返回的片段没有 speaker 标签，发言人由 DeepSeek 在润色阶段
  根据语义推断，属最佳猜测。提供 `--speaker-alias` / 参会人名单能提高准确度，但不保证正确。
- **22MB 上限**：Fish 上传上限约 22MB，脚本会用 ffmpeg 自动按时长分块（默认约 240s），
  分块结果带缓存（同名 `.fish-chunks-*` 目录），中断可续跑。
- **输入格式**：iPhone 语音备忘录的 `.qta` 会自动转成 `.m4a`（ffmpeg，回退 macOS
  `afconvert`）；wav/mp3/flac 等在分块时自动重编码为 AAC。原始文件名仍记录在 memo 里。
- **最新录音按文件名日期判断**：iCloud 同步会刷新文件 mtime，所以 `find_latest_recording.sh`
  以文件名里的 `YYYYMMDD` 前缀判断「今天/最新」，mtime 仅作兜底排序。录音文件名需带日期前缀。
- **DeepSeek 直连**：润色走 DeepSeek 官方 API，不经 Volcengine Ark；如需换平台改
  `DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL`。
- **keyterms 是个人词表**：`--keyterms-file` 指向的术语表因人/因行业而异。仓库只放
  `keyterms.example.txt` 模板；复制成 `keyterms.txt`（已 gitignore）填自己的词，不会被提交。
- **格式因人而异**：`weekly-meeting-review` 的版式按作者习惯（见
  `references/format-skeleton.md`），`meeting-dashboard` 的布局/位置同理，复用时按需调整。
