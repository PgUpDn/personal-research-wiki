---
title: "Page Formats"
aliases:
  - "Page Formats"
note_type: "system"
last_compiled: 2026-09-30
---

# Page Formats

- Last refreshed: 2026-09-30
- Schema version: `research-wiki-pdf-v1`

## Design Goals

- Keep `raw/` immutable and move machine-generated transcript artifacts into `_meta/`.
- Put Dataview-friendly metadata in frontmatter and graph-friendly wikilinks in body sections.
- Keep generated source pages compact enough for browsing and Q&A, while preserving long transcripts in cache notes.
- Prefer flat scalar and list properties over deeply nested YAML so Obsidian Properties and Dataview stay easy to query.

## Open Knowledge Format Export

The native `wiki/` schema remains optimized for Obsidian. A deterministic compatibility export under `output/okf/` targets Open Knowledge Format v0.2 without changing source or wiki documents.

The export provides:
- required OKF `type` metadata and standard Markdown links
- structured `sources` provenance with stable identifiers and source timestamps when available
- explicit `generated`, `status`, and active-project `stale_after` signals
- optional explicit verification via flat native fields `okf_verified_by` and `okf_verified_at`
- progressive `index.md` files and a newest-first `log.md`
- `manifest.json`, `conformance.json`, and a portable ZIP archive

Trust tiers are derived only from explicit verification events; compiler output is not mislabeled as human-reviewed content.

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
- `github_links`
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

## LaTeX Cache Notes

Location: `_meta/converted_sources/*.md`

Frontmatter:
- `title`
- `note_type: source_cache`
- `schema_version`
- `source_id`
- `source_tex`
- `source_kind: raw_tex`
- `authors`
- `year`
- `converted_at`
- `conversion_pipeline: pandoc-latex-to-markdown`
- `cache_role: latex-source-cache`
- `source_digest`
- `dependencies`
- `tags`

Sections:
- `## Conversion Snapshot`
- `## Abstract` when present
- `## Extracted Markdown`

## Reconstructed Clipping Cache Notes

Location: `_meta/converted_sources/_sanitized_clippings/<source-hash>/*.md`

Preserve the clipping's original frontmatter and add:
- `sanitized_from`
- `sanitization_pipeline`
- `source_digest`
- `sanitized_artifact_blocks`
- `reconstructed_mermaid_blocks`
- `mermaid_recovery_source`
- `mermaid_sources_digest`

Replace only high-confidence rendered Mermaid artifact fences and retain ordinary code fences and surrounding article text. Generate a cache only when the recovered definition count exactly matches the artifact count; otherwise compile the immutable clipping unchanged.

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
- `github_links`
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
- `curated_note` only when `wiki/curated/<slug>.md` exists
- `sources`
- `source_pages`
- `related`
- `tags`
- `last_compiled`

Sections:
- `## Definition`
- `## Curated notes` only when `wiki/curated/<slug>.md` exists (see Curated Concept Notes)
- `## What The Sources Emphasize`
- `## Coverage`
- `## Related Concepts`
- `## Representative sources`
- `## Provenance`

## Curated Concept Notes

Location: `wiki/curated/<slug>.md`, at most one optional file per concept catalog slug (the slug is the file stem).

Frontmatter:
- `title`
- `note_type: curated`
- `concept: <slug>`
- `sources` (raw paths the notes are distilled from)
- `tags`
- `last_edited`

What compile does:
- When `wiki/curated/<slug>.md` exists, `compile` strips its frontmatter and a leading H1 and inlines the body verbatim into `wiki/concepts/<slug>.md` as `## Curated notes`, placed right after `## Definition` and preceded by the italic line `Hand-maintained in wiki/curated/<slug>.md; the other sections are compiler output.` Wikilinks inside the curated text are preserved exactly as written.
- A concept with a curated file, or with `keep_without_sources: true` in its catalog entry, is generated even when no source matches its aliases (`source_count: 0`, `Representative sources: none matched yet`) and is never deleted as stale.
- Curated files are fragments, not pages. The lint orphan scan, `INDEX.md`, the OKF and HTML exports, and the CLI search corpus enumerate only the top-level `wiki/*.md`, `wiki/concepts/`, `wiki/sources/`, `wiki/projects/`, and `wiki/derived/`, so `wiki/curated/` never appears as a standalone document; the lint additionally skips any document declaring `note_type: curated`.
- Curated text is the ONLY place hand-written concept prose survives: every other section of `wiki/concepts/*.md` is rewritten on each compile, so edit `wiki/curated/<slug>.md`, never the generated concept page.

Writing guidance:
- Use `###` headings inside the curated body (the generated page owns `#` and `##`).
- Cite the raw source of record with a wikilink to its source page or a backticked `raw/` path; do not restate facts the source does not contain.

## Project Pages

Location: `wiki/projects/*.md`

Frontmatter:
- `title`
- `aliases`
- `note_type: project`
- `project_id`
- `project_name`
- `project_level: programme | subproject`
- `parent_project_id` for subprojects
- `project_status`
- `snapshot_date`
- `sources`
- `related`
- `tags`

Sections:
- `## Programme Thesis` or `## Project Thesis`
- `## Evidence Ledger`
- `## Milestone Gates`
- `## Negative Evidence and Open Gaps`
- `## Next Execution Focus`
- `## Source Package`

## Querying Notes

- Query frontmatter fields such as `note_type`, `year`, `lead_author`, `concept_group`, and `source_count` from Dataview.
- Keep the same concepts both in frontmatter and body lists so Dataview remains structured while Graph/backlinks stay reliable.
- Treat cache notes as machine-oriented transcript storage; treat source pages as the default human and agent landing pages.
