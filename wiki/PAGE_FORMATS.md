---
title: "Page Formats"
aliases:
  - "Page Formats"
note_type: "system"
last_compiled: 2026-04-05
---

# Page Formats

- Last refreshed: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

## Design Goals

- Keep `raw/` immutable and move machine-generated transcript artifacts into `_meta/`.
- Put Dataview-friendly metadata in frontmatter and graph-friendly wikilinks in body sections.
- Keep generated source pages compact enough for browsing and Q&A, while preserving long transcripts in cache notes.
- Prefer flat scalar and list properties over deeply nested YAML so Obsidian Properties and Dataview stay easy to query.

## PDF Cache Notes

Location: `_meta/converted_sources/*.md`

Frontmatter:
- `title`
- `note_type: source_cache`
- `schema_version`
- `source_id`
- `source_pdf`
- `source_kind`
- `authors`
- `year`
- `venue`
- `doi`
- `arxiv_id`
- `page_count`
- `page_image_dir`
- `converted_at`
- `conversion_pipeline`
- `cache_role`
- `tags`

Sections:
- `## Conversion Snapshot`
- `## Preview`
- `## Extracted Markdown`

## Source Pages

Location: `wiki/sources/*.md`

Frontmatter:
- `title`
- `aliases`
- `note_type: source`
- `schema_version`
- `source_id`
- `citation_key`
- `source_kind`
- `source_status`
- `year`
- `lead_author`
- `venue`
- `doi`
- `arxiv_id`
- `authors`
- `sources`
- `cache_path`
- `page_image_dir`
- `page_count`
- `concepts`
- `domains`
- `themes`
- `section_index`
- `tags`
- `related`
- `last_compiled`

Sections:
- `## Citation & Files`
- `## TL;DR`
- `## Abstract`
- `## Key Concepts`
- `## Research Signals`
- `## Reading Map`
- `## Provenance`

## Concept Pages

Location: `wiki/concepts/*.md`

Frontmatter:
- `title`
- `aliases`
- `note_type: concept`
- `schema_version`
- `concept_group`
- `source_count`
- `sources`
- `source_pages`
- `related`
- `tags`
- `last_compiled`

Sections:
- `## Definition`
- `## What The Sources Emphasize`
- `## Coverage`
- `## Related Concepts`
- `## Representative sources`
- `## Provenance`

## Querying Notes

- Query frontmatter fields such as `note_type`, `year`, `lead_author`, `concept_group`, and `source_count` from Dataview.
- Keep the same concepts both in frontmatter and body lists so Dataview remains structured while Graph/backlinks stay reliable.
- Treat cache notes as machine-oriented transcript storage; treat source pages as the default human and agent landing pages.
