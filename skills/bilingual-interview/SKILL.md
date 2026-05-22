---
name: bilingual
description: Use when the user wants an English interview, podcast, or conversation transcript turned into polished bilingual Markdown with Chinese added under each speaker turn, or when an existing bilingual transcript needs reformatting turn by turn.
---

# Bilingual Interview

Convert English interview-style transcripts into clean bilingual Markdown that is easy to read in Obsidian or similar note apps.

## Use This Skill For

- English podcast, interview, fireside chat, or Q&A transcripts
- Markdown files with clear speaker labels
- Requests to add Chinese under each English turn
- Requests to replace poor Chinese with a fresh translation
- Requests to reflow bilingual transcript formatting without changing meaning

## Default Output Format

Unless the user asks for a different layout, format each turn like this:

```md
Speaker Name

English paragraph

Chinese paragraph
```

Rules:

- Keep the original English.
- Put the Chinese directly under the matching English turn.
- Split paragraphs only when the speaker changes.
- Within one speaker turn, collapse extra line breaks into one English paragraph and one Chinese paragraph.
- Do not prefix the translation with labels like `中文：` unless the user explicitly asks for labels.
- Preserve frontmatter, embeds, titles, and non-transcript metadata.

## Workflow

1. Inspect the file and identify the speaker markers.
2. Preserve existing metadata and non-dialogue scaffolding.
3. For each speaker turn, produce a fluent Chinese translation rather than lightly editing bad machine translation.
4. If the file already contains Chinese, replace low-quality Chinese while keeping the English aligned.
5. Reflow formatting to the user’s requested style after translation is complete.
6. Before overwriting the source file, create a backup when the change is substantial.
7. Verify that every speaker turn still exists and that no translation blocks were dropped.

## Translation Style

- Prefer natural, publication-quality Chinese over literal word-for-word translation.
- Keep names, product names, and company names accurate and consistent.
- Preserve the speaker’s intent, tone, and level of certainty.
- For sponsor reads, asides, or malformed blocks, keep the closest sensible structure and avoid inventing content.
- If a sentence is messy in the source, clarify it in Chinese without adding new claims.

## Formatting Edits Without Retranslation

If the user only wants layout changes:

- Do not rewrite translation content unless needed to fix obvious breakage.
- Reflow by speaker turn.
- Keep English and Chinese in paired order.
- Remove or add translation labels only if requested.

## Verification

After editing:

- Spot-check the opening section and at least one middle section.
- Confirm whether `中文：` or other temporary markers remain when they should not.
- If possible, check that each speaker label is still followed by both English and Chinese content.
