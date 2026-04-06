# My Research Workspace

Open this folder directly in Obsidian. The project is structured so `raw/` stays immutable, the LLM incrementally compiles source pages and concept pages into `wiki/`, and downstream tools render answers, slides, and reports into `output/`.

This repository is meant to track the research vault itself:

- `raw/` source material
- `wiki/` compiled knowledge pages
- `Templates/` capture and note templates
- selected `.obsidian/` configuration
- compiler code in `_meta/`

It intentionally ignores local caches, rendered PDF page images, transient outputs, and per-device workspace state.
Raw PDF files also stay local and are not committed to GitHub; the repository tracks the research workspace structure rather than the full document archive.
This public version keeps `raw/` in example mode while retaining example compiled wiki pages and tooling.

## Workflow

1. Ingest source material into `raw/` as-is.
2. Use the compiler or watcher to transcribe PDFs into `_meta/converted_sources/`, then refresh `wiki/sources/`, `wiki/concepts/`, `wiki/INDEX.md`, and `wiki/LOG.md`.
3. Ask questions against the maintained wiki and write the results back out as markdown or Marp slides.
4. File especially useful outputs into `wiki/derived/` so the knowledge base compounds over time.
5. Review `wiki/LINT_AND_HEAL.md` to keep the wiki healthy and spot new concept candidates.
6. Treat [AGENTS.md](AGENTS.md) as the schema that defines how the LLM should maintain this workspace.

## Key Paths

| Path | Purpose |
| --- | --- |
| `raw/` | immutable source documents, web clips, notes, and local images |
| `wiki/sources/` | one wiki page per source |
| `wiki/concepts/` | synthesized concept articles |
| `wiki/` | index, system notes, log, lint report, and filed-back outputs |
| `output/` | generated answers, slide decks, charts, and reports |
| `_meta/` | compiler scripts, state, PDF caches, rendered page images, node tools, and watcher infrastructure |

## Useful Commands

```bash
.venv/bin/python _meta/scripts/wiki_cli.py compile --root .
.venv/bin/python _meta/scripts/wiki_cli.py watch --root . --once
.venv/bin/python _meta/scripts/wiki_cli.py search --root . "meshgraphnets"
.venv/bin/python _meta/scripts/wiki_cli.py ask --root . "What are the most common themes in the CFD papers?" --file-into-wiki
.venv/bin/python _meta/scripts/wiki_cli.py export-html --root .
```

## Obsidian Setup

- Open the repository root as the vault.
- Community plugin IDs are tracked in `.obsidian/community-plugins.json`.
- QuickAdd and Templater workflow configuration is tracked in:
  - `.obsidian/plugins/quickadd/data.json`
  - `.obsidian/plugins/templater-obsidian/data.json`
- The template library lives in `Templates/`.
- Local plugin bundles and workspace state are not part of the repository.

## Obsidian Features

- Graph view is already enabled in this vault.
- Dataview and Marp are installed as community plugins.
- A starter Dataview page lives at [DASHBOARD.md](wiki/DASHBOARD.md).
- Git is intended to track `raw/`, `wiki/`, and selected config, while ignoring local caches and transient outputs.
