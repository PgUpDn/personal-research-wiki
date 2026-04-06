---
title: "System Overview"
aliases:
  - "System Overview"
note_type: "system"
last_compiled: 2026-04-05
---

# System Overview

- Last refreshed: 2026-04-05
- Raw sources represented in the wiki: 19
- Source pages: 19
- Concept articles: 34

## Main Pipeline

1. `raw/` stores source material as-is. It is the immutable source-of-truth layer.
2. PDF transcription caches and rendered page images live under `_meta/`, not in `raw/`, so the compiler can process sources without mutating them.
3. The compiler incrementally refreshes `wiki/sources/*.md`, `wiki/concepts/*.md`, `wiki/INDEX.md`, and `wiki/LOG.md`.
4. The Q&A layer reads the maintained wiki, renders answers into markdown, Marp slides, or other output files, and can file valuable outputs back into `wiki/derived/`.

## Three Layers

- `raw/`: immutable source documents, web clips, datasets, and local assets.
- `wiki/`: LLM-maintained markdown pages including source pages, concept pages, indexes, logs, and filed-back notes.
- `AGENTS.md`: the in-repo schema that tells the LLM how to ingest, query, and maintain this workspace.
- `wiki/PAGE_FORMATS.md`: the canonical frontmatter and section layouts for generated cache, source, and concept notes.
- `wiki/PAPER_TEMPLATE.md`: the rationale and recommended structure for PDF-derived literature notes.

## Support Layer

- Open the repository root directly in Obsidian to browse `raw/`, `wiki/`, `_meta/`, and `output/` from one vault.
- `LINT_AND_HEAL.md` tracks broken links, orphan pages, sparse concepts, low-coverage sources, and suggested cleanup passes.
- `_meta/scripts/wiki_cli.py` is the unified CLI for compile, watch, search, ask, lint, and filing outputs back into the wiki.

## Directory Map

| Path | Purpose |
| --- | --- |
| `raw/` | immutable source documents and user-managed local assets |
| `wiki/sources/` | one wiki page per source document, maintained by the compiler |
| `wiki/concepts/` | synthesized concept pages built across many sources |
| `wiki/derived/` | valuable outputs filed back into the knowledge base |
| `output/` | generated answers, slide decks, charts, and reports |
| `_meta/` | compiler state, cached PDF transcriptions, rendered page images, scripts, and tooling |

## Working Rhythm

- Ingest with tools like Obsidian Web Clipper and save related source images locally in `raw/`.
- Let the watcher or compile command keep source pages, concept pages, the index, and the log up to date.
- Ask questions through the CLI and render results back into markdown so Obsidian remains the frontend.
- Run lint passes regularly so the wiki keeps improving instead of drifting.
