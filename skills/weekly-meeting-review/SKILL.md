---
name: weekly-meeting-review
description: Look at all the new entries in the meeting memo folder, then write this week's meeting summary into the analysis folder, matching the exact format of the previous weekly summaries. Use when the user wants the weekly meeting review / 本周会议总结.
---

# Weekly Meeting Review

Each week, read the new meeting memos (and any diary entries) and write one
"this week" meeting summary into the analysis folder, following the same format as
the existing weekly summaries already there.

## Folders
- Meeting memos (source): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/meeting memo`
- Analysis (output): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/analysis`
  - TODO: confirm the exact analysis folder name/path in the vault.

## Workflow
1. Open the most recent existing weekly summary in the analysis folder and treat it
   as the canonical template. If none exists, use `references/format-skeleton.md`.
   Match its structure, section order, table columns, callouts, and language.
2. Look at all the **new** entries in the meeting memo folder — memos added since
   the last weekly summary. Use the filename `YYYYMMDD` date prefix to pick the
   week's memos (default: the ISO week, or memos newer than the last summary).
   Include any diary entries from the same week if present.
3. Read each memo's summary section (not the full transcript) and synthesize across
   meetings into the structure below.
4. Write the result as a new file in the analysis folder, named like the existing
   weekly summaries (e.g. `<YYYY>-W<WW>`).
5. Report the week covered, which memos/diaries were included, and the new file name.

## Required Structure
Follow the previous file; the established shape is:
1. **Title** — `# Weekly Meeting Summary | <YYYY>-W<WW>（M/D–M/D）`.
2. **Opening overview** — one blockquote paragraph: meeting count by category, the
   week's heaviest throughline and its driver, then 2nd/3rd throughlines.
3. **本周会议列表** — table: `日期 | 会议 | 类型 | 主要命题`.
4. **主线一/二/…** — one section per major thread. Each: a lead paragraph, then
   structured facts (often a `维度 | 事实` table), key quotes as blockquotes, and a
   "含义/结论" note tying it to the thesis, framework, or valuation anchor. For deal
   terms, use a "previous ultimatum → final state" comparison table. Expert-call
   threads end with "对 framework 的含义" and "需修正的既有假设".
5. **值得深入思考的问题** — open questions, including a `> [!note] Esther Lesson:`
   callout for personal reflection.
6. **与过去几周的对比** — 延续的主线 / 新增主线 / 观点分歧与修正 / 累积 unresolved 追问.
7. **本周结论** — numbered conclusions with drivers and dates.
8. **后续待跟踪项 Tracker（W<下周> 起）** — table: `项目 | 待办 | 截止/触发条件`,
   carrying forward unresolved items from prior weeks.
9. **Footer** — `*本 Summary 由 Claude 根据 <N> 份会议记录 + <M> 篇日记深度分析生成 | <date>（W<WW> 完结）*`.

## Decision Rules
- Match the previous file's format exactly — the user wants continuity, not a new
  layout. Reuse its Obsidian markup conventions (`==高亮==` for key judgments,
  `<u>下划线</u>` for genuinely unresolved points, `> [!note]` callouts).
- Synthesize across meetings (themes, decisions, reversals, follow-ups). Do not just
  stack per-meeting summaries.
- Carry the Tracker forward: keep prior unresolved items and mark overdue ones.
- Preserve concrete numbers, dates, names, valuations, and commitments — these are
  the point of the review.
- Select memos by the filename date prefix, consistent with `daily-meeting-minute`.
- Read memos only; never edit or move them.
- If no new memos exist for the period, say so instead of inventing content.
- For per-meeting depth, defer to `interview-summary`; this skill is the weekly
  cross-meeting layer.

## Reference Map
- `references/format-skeleton.md`: redacted structural skeleton of the weekly
  summary, used when no prior file is available as a template.
