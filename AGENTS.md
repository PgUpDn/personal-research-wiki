# My Research Wiki Schema

This repository follows the "LLM wiki" pattern: `raw/` is the immutable source-of-truth layer, `wiki/` is the LLM-maintained knowledge base, and this file is the schema that tells the agent how to operate on both.

## Core Rules

1. Never modify source documents in `raw/`.
2. Never move source documents out of `raw/`.
3. Put PDF transcription caches, rendered page images, and other machine-generated intermediates in `_meta/`.
4. Treat `wiki/` as fully LLM-owned. Create, revise, and link pages there freely.
5. Keep `wiki/INDEX.md` and `wiki/LOG.md` current whenever the wiki changes.
6. Prefer `[[wiki-links]]` between wiki pages.

## Directory Roles

- `raw/`: immutable source documents, clipped articles, datasets, notes, and user-managed local assets.
- `wiki/sources/`: one LLM-maintained page per source document.
- `wiki/concepts/`: synthesized concept pages spanning many sources.
- `wiki/derived/`: answers, comparisons, and other outputs worth filing back into the knowledge base.
- `output/`: generated artifacts that may or may not later be filed back into `wiki/derived/`.
- `_meta/converted_sources/`: machine-generated markdown caches for PDFs.
- `_meta/source_page_images/`: rendered page images used during PDF transcription.
- `wiki/LOG.md`: append-only chronology of compiles, queries, and lint passes.

## Ingest Workflow

When new sources appear:

1. Read the new raw source.
2. If it is a PDF, transcribe it into `_meta/converted_sources/` without changing the original PDF.
3. Create or update a source page in `wiki/sources/`.
4. Update the relevant concept pages in `wiki/concepts/`.
5. Refresh `wiki/INDEX.md`.
6. Append an entry to `wiki/LOG.md`.

## Query Workflow

When answering questions:

1. Read `wiki/INDEX.md` first.
2. Pull in relevant source pages, concept pages, and prior derived notes.
3. Write the result into `output/` as markdown, Marp, charts, or similar.
4. If the result is durable, file it into `wiki/derived/`.
5. Append a query entry to `wiki/LOG.md`.

## Lint Workflow

Periodically check for:

- broken wiki-links
- orphan pages
- contradictions or stale claims
- concepts mentioned repeatedly but lacking their own page
- low-coverage sources that only map to broad fallback concepts

Record lint outcomes in `wiki/LINT_AND_HEAL.md` and append a lint entry to `wiki/LOG.md`.

## Style

- Prefer flat frontmatter fields over deep nested objects so Obsidian Properties and Dataview stay easy to query.
- Keep the same important links both in frontmatter and in body sections: frontmatter for Dataview, body `[[wiki-links]]` for graph/backlinks.
- Use source pages as the default human and agent landing pages for individual documents.
- Use concept pages as the place to synthesize across documents.
- Keep raw-source paths explicit in frontmatter so provenance stays visible.

## Schema Version

- Current schema version: `research-wiki-pdf-v1`

## Generated Page Types

### 1. PDF Cache Notes

- Location: `_meta/converted_sources/*.md`
- Role: machine-oriented transcript storage for PDFs
- Required frontmatter:
  - `title`
  - `note_type: source_cache`
  - `schema_version`
  - `source_id`
  - `source_pdf`
  - `source_kind`
  - `authors`
  - `year`
  - `page_count`
  - `page_image_dir`
  - `converted_at`
  - `conversion_pipeline`
  - `cache_role`
  - `tags`
- Required sections:
  - `## Conversion Snapshot`
  - `## Preview`
  - `## Extracted Markdown`

### 2. Source Pages

- Location: `wiki/sources/*.md`
- Role: compact, queryable document cards generated from raw sources and caches
- Required frontmatter:
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
- Required sections:
  - `## Citation & Files`
  - `## TL;DR`
  - `## Abstract`
  - `## Key Concepts`
  - `## Research Signals`
  - `## Reading Map`
  - `## Provenance`

### 3. Concept Pages

- Location: `wiki/concepts/*.md`
- Role: synthesized concept notes spanning many source pages
- Required frontmatter:
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
- Required sections:
  - `## Definition`
  - `## What The Sources Emphasize`
  - `## Coverage`
  - `## Related Concepts`
  - `## Representative sources`
  - `## Provenance`

## PDF-Specific Rules

- Do not inline all rendered page images into cache notes; show at most a light preview and keep the directory path in metadata.
- Prefer title detection from the transcript over truncated filename titles when the transcript clearly contains a richer heading.
- Extract lightweight bibliography fields such as `year`, `lead_author`, `authors`, and `citation_key` when possible, but never mutate the raw filename to enforce them.
- Keep long transcript content in `_meta/converted_sources/`; keep `wiki/sources/` readable enough for Obsidian browsing, graphing, and Q&A.
