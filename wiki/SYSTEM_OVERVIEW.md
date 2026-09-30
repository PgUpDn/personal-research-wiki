---
title: "System Overview"
aliases:
  - "System Overview"
note_type: "system"
last_compiled: 2026-09-30
---

# System Overview

- Last refreshed: 2026-09-30
- Immutable source files tracked: 329
- Unique source pages: 321
- Duplicate source variants merged into canonical pages: 8
- Concept articles: 47

## Main Pipeline

1. `raw/` stores source material as-is. It is the immutable source-of-truth layer.
2. PDF transcription caches and rendered page images live under `_meta/`, not in `raw/`, so the compiler can process sources without mutating them.
3. The compiler incrementally refreshes source pages, concept pages, the project catalog, `wiki/INDEX.md`, and `wiki/LOG.md`.
4. The Q&A layer reads the maintained wiki, renders answers into markdown, Marp slides, or other output files, and can file valuable outputs back into `wiki/derived/`.
5. The interchange layer exports the maintained wiki as an OKF v0.2 bundle with standard links, structured provenance, lifecycle signals, progressive indexes, and deterministic conformance checks.

## Three Layers

- `raw/`: immutable source documents, web clips, datasets, and local assets.
- `wiki/`: LLM-maintained markdown pages including projects, source pages, concept pages, indexes, logs, and filed-back notes.
- `AGENTS.md`: the in-repo schema that tells the LLM how to ingest, query, and maintain this workspace.
- `wiki/PAGE_FORMATS.md`: the canonical frontmatter and section layouts for generated cache, source, and concept notes.
- `wiki/PAPER_TEMPLATE.md`: the rationale and recommended structure for PDF-derived literature notes.
- `output/okf/`: the portable Open Knowledge Format v0.2 compatibility bundle.

## Support Layer

- Open `/Users/yangx2/Documents/my-research` directly in Obsidian to browse `raw/`, `wiki/`, `_meta/`, and `output/` from one vault.
- `LINT_AND_HEAL.md` tracks broken links, orphan pages, sparse concepts, low-coverage sources, and suggested cleanup passes.
- `_meta/scripts/wiki_cli.py` is the unified CLI for compile, watch, search, ask, lint, OKF export, and filing outputs back into the wiki.

## Directory Map

| Path | Purpose |
| --- | --- |
| `raw/` | immutable source documents and user-managed local assets |
| `wiki/sources/` | one wiki page per source document, maintained by the compiler |
| `wiki/concepts/` | synthesized concept pages built across many sources |
| `wiki/curated/` | hand-maintained curated notes, inlined into the matching concept page at compile time (fragments, not standalone pages) |
| `wiki/projects/` | active research programmes and project dossiers |
| `wiki/derived/` | valuable outputs filed back into the knowledge base |
| `output/` | generated answers, slide decks, charts, and reports |
| `output/okf/` | OKF v0.2 exchange bundle, machine-readable graph manifest, and conformance report |
| `_meta/` | compiler state, cached PDF transcriptions, rendered page images, scripts, and tooling |

## Working Rhythm

- Ingest with tools like Obsidian Web Clipper and save related source images locally in `raw/`.
- Let the watcher or compile command keep source pages, concept pages, the index, and the log up to date.
- Ask questions through the CLI and render results back into markdown so Obsidian remains the frontend.
- Run lint passes regularly so the wiki keeps improving instead of drifting.
