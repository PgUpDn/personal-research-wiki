# PDF Paper Template

- Last reviewed: 2026-04-05
- Status: recommended working template for PDF-derived source pages

## What I looked at

- Obsidian's current metadata model treats note properties and aliases as first-class structure, so templates should keep important fields in flat frontmatter rather than burying everything in prose.
- Dataview works best when those fields are easy to query as scalars and lists.
- Zotero-oriented literature-note templates often separate the citation layer from the reading / annotation layer.
- BibLib shows the far end of the spectrum: full bibliographic metadata in frontmatter, which is powerful but heavier than this vault needs for day-to-day reading and LLM maintenance.

## Reference Patterns Worth Borrowing

### 1. Obsidian / Dataview pattern

What to borrow:
- Keep metadata flat and typed.
- Use aliases for alternate paper titles and citekeys.
- Use list fields for authors, tags, and linked concepts.

Why it fits this repo:
- The wiki compiler, Dataview, and graph view all benefit from predictable frontmatter.
- Flat fields are easier to lint, migrate, and query than nested citation objects.

### 2. Zotero literature-note pattern

What to borrow:
- Separate bibliographic metadata from note content.
- Give the human-facing note stable sections like summary, abstract, notes, and annotations.
- Keep the raw highlight / extraction layer distinct from the synthesized note.

Why it fits this repo:
- `_meta/converted_sources/` can remain the machine transcript layer.
- `wiki/sources/` can become the compact paper card that people and agents actually read.

### 3. Full bibliographic frontmatter pattern

What to borrow:
- Stable IDs like citekeys.
- Author, year, DOI, and URL slots where available.
- The idea that references should remain plain markdown, not a hidden database.

What not to copy directly:
- Full CSL-JSON frontmatter is more detailed than this workflow currently needs.
- Deep or highly nested metadata is awkward for Obsidian properties and noisier for LLM-maintained pages.

## Recommended Template For This Vault

### A. PDF cache note

Location:
- `_meta/converted_sources/*.md`

Purpose:
- Preserve the transcript faithfully.
- Keep page-image provenance.
- Avoid mixing raw transcript with higher-level interpretation.

Recommended sections:
1. `## Conversion Snapshot`
2. `## Preview`
3. `## Extracted Markdown`

### B. Source page

Location:
- `wiki/sources/*.md`

Purpose:
- Be the default human and agent landing page for one paper.
- Keep enough metadata for Dataview and future export.
- Stay shorter and cleaner than the transcript cache.

Recommended frontmatter:
- `title`
- `aliases`
- `note_type: source`
- `schema_version`
- `source_id`
- `citation_key`
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

Recommended body:
1. `## Citation & Files`
2. `## TL;DR`
3. `## Abstract`
4. `## Key Concepts`
5. `## Research Signals`
6. `## Reading Map`
7. `## Provenance`

Why this is the best fit:
- It is much lighter than full bibliography schemas.
- It still keeps enough structure for HTML export, Dataview, and future enrichment.
- It matches the real split in this repo between transcript cache and synthesized wiki page.

### C. Optional future upgrades

If later we want richer paper cards, the safest additions are:
- `doi`
- `arxiv_id`
- `venue`
- `research_question`
- `method_snapshot`
- `key_findings`
- `limitations`

These should only be added once extraction quality is reliable enough to avoid hallucinated structure.

## Decision

This repo should use a hybrid template:
- Flat Obsidian/Dataview-friendly frontmatter.
- A paper-card body inspired by literature-note templates.
- A separate transcript cache for the full PDF conversion output.

That is the most compatible option for:
- `Obsidian + Dataview`
- incremental LLM compilation
- HTML export
- later schema evolution without breaking old notes

## References

- Obsidian aliases: [obsidian.md/help/aliases](https://obsidian.md/help/aliases)
- Dataview metadata docs: [blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/](https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/)
- Zotero template examples: [rodrigolourencofarinha/Obsidian-Zotero-Templates](https://github.com/rodrigolourencofarinha/Obsidian-Zotero-Templates)
- Bibliography-first reference notes: [callumalpass/obsidian-biblib](https://github.com/callumalpass/obsidian-biblib)
