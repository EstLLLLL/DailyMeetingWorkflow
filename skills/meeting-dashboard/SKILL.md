---
name: meeting-dashboard
description: Build or refresh an Obsidian dashboard note that indexes all meeting memos in the meeting memo folder (date, title, participants, link). Use when the user wants an overview/index of their meeting memos, or after new memos are added and the dashboard needs updating.
---

# Meeting Dashboard

Maintain a single Obsidian note that indexes every meeting memo so the user can
scan all meetings at a glance and jump to any memo.

> DRAFT: first version. The exact dashboard layout, sort order, and grouping are
> the user's call — adjust the conventions below to match what they actually want.

## Folders
- Meeting memos (source): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/meeting memo`
  - Same as `VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR`.
- Dashboard note (output): `<vault>/Esther Workspace/meeting memo/Meeting Dashboard.md`
  - TODO: confirm the file name and location the user prefers.

## Workflow
1. List the memo files in the meeting memo folder. Each memo's filename starts
   with a `YYYYMMDD` date prefix and continues with the meeting title.
2. For each memo, derive:
   - date (from the filename prefix)
   - title (filename minus the date prefix and extension)
   - link (Obsidian wikilink `[[filename-without-extension]]`)
   - participants / keywords, if the memo records them near the top
3. Write the dashboard note as a table, newest first, grouped by month.
4. Do not duplicate memo content into the dashboard — link to it. The dashboard is
   an index, not a copy.
5. Report how many memos were indexed and whether any new ones were added since
   the last refresh.

## Default Layout
```md
# Meeting Dashboard

## 2026-05
| 日期 | 会议 | 参会人 | 链接 |
|---|---|---|---|
| 2026-05-22 | 字节火山云架构师 | … | [[20260522 字节火山云架构师]] |
| 2026-05-21 | 腾讯云解决方案总监 | … | [[20260521 腾讯云解决方案总监]] |
```

## Dataview Alternative
If the user has the Obsidian Dataview plugin, a live query avoids manual refresh.
Offer this instead of a static table when appropriate:
```dataview
TABLE participants, keywords
FROM "Esther Workspace/meeting memo"
WHERE file.name != this.file.name
SORT file.name DESC
```
TODO: this assumes memos expose `participants`/`keywords` as frontmatter or inline
fields. The current `volcengine-transcribe` memo does not add frontmatter, so
either add it there or drop these columns.

## Decision Rules
- Sort newest first by the filename date prefix (consistent with
  `daily-meeting-minute`).
- Never edit or move the underlying memos; only read them and write the dashboard.
- If the dashboard note already exists, refresh it in place rather than creating a
  duplicate.
- Keep the dashboard a pure index. Summaries belong in the memos and in the weekly
  review, not here.
