# Personal Research Wiki

Personal Research Wiki is an Obsidian-based research workspace for collecting raw source material, compiling it into a linked markdown knowledge base, and querying that knowledge base through LLM-assisted workflows.

The repository is organized around a simple idea: keep source material in source inboxes like `raw/` and `Clippings/`, let the compiler maintain structured knowledge in `wiki/`, and render downstream answers, slides, and reports into `output/`.

## Overview

This project tracks the research vault itself, including:

- source material in `raw/` and `Clippings/`
- compiled knowledge pages in `wiki/`
- capture and note templates in `Templates/`
- selected Obsidian configuration in `.obsidian/`
- compiler and export tooling in `_meta/`

The public version of this repository is intentionally lightweight. Large private PDFs, rendered page caches, transient outputs, and machine-specific workspace state are kept out of version control.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `raw/` | source documents, PDFs, and local assets managed by the user |
| `Clippings/` | Obsidian Web Clipper captures that should be treated as raw source material |
| `wiki/sources/` | one wiki page per source document |
| `wiki/concepts/` | synthesized concept pages spanning multiple sources |
| `wiki/projects/` | active programme and subproject dossiers linking evidence, milestones, gaps, and next actions |
| `wiki/derived/` | durable answers and outputs filed back into the wiki |
| `wiki/` | index, system notes, log, health checks, and derived pages |
| `output/` | generated answers, slides, charts, and reports |
| `_meta/` | compiler scripts, state, PDF caches, and export tooling |
| `Templates/` | QuickAdd and Templater templates for structured capture |

## Research Workflow

1. Add source material to `raw/` or `Clippings/`.
2. Run the compiler or watcher to convert PDFs with Microsoft MarkItDown and LaTeX packages with Pandoc, refresh source pages, update concept pages, and keep the wiki index current. When matching `.tex` and `.pdf` files are adjacent, the compiler indexes the LaTeX source and keeps the PDF as the visual snapshot.
3. Organize active programmes and their subprojects in `wiki/projects/` so hierarchy, evidence, and milestones remain visible across sources.
4. Query the compiled wiki to generate notes, comparisons, reports, or presentations.
5. File valuable outputs back into `wiki/derived/` so the knowledge base compounds over time.
6. Review `wiki/LINT_AND_HEAL.md` to identify broken links, low-coverage areas, and opportunities for refinement.

The schema and maintenance rules for the vault are documented in [AGENTS.md](AGENTS.md).

## Quick Start

Open the repository root directly in Obsidian so that `raw/`, `Clippings/`, `wiki/`, `_meta/`, and `output/` remain visible within a single vault.

Common commands:

```bash
.venv/bin/python _meta/scripts/wiki_cli.py compile --root .
.venv/bin/python _meta/scripts/wiki_cli.py watch --root . --once
.venv/bin/python _meta/scripts/wiki_cli.py search --root . "meshgraphnets"
.venv/bin/python _meta/scripts/wiki_cli.py ask --root . "What are the most common themes in the CFD papers?" --file-into-wiki
.venv/bin/python _meta/scripts/wiki_cli.py export-html --root .
```

Install the Python conversion stack into a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r _meta/requirements.txt
```

### Document conversion backends

- **PDF to Markdown:** [Microsoft MarkItDown](https://github.com/microsoft/markitdown) is the default backend. The compiler resolves the CLI from `markitdown_cli` in `_meta/config.json`, then from the active `PATH`. Extracted Markdown is stored under `_meta/converted_sources/`; source PDFs remain unchanged.
- **LaTeX to Markdown:** Pandoc handles top-level `.tex` manuscripts and records a digest of the package dependencies. If a same-stem PDF is present, the LaTeX package is indexed as the source of truth and the PDF is retained only as a visual snapshot.
- **Conversion command:** `.venv/bin/python _meta/scripts/wiki_cli.py convert --root .` converts changed sources; add `--force` to rebuild their caches.

The LaTeX backend requires `pandoc` on `PATH` (`brew install pandoc` on macOS). Backend names and executable locations can be overridden in `_meta/config.json`.

MarkItDown extracts embedded text but is not an OCR engine. Image-only or scanned PDFs can therefore return empty Markdown; the compiler reports these conversion failures and exits non-zero instead of silently treating stale caches as successful output. Configure the optional `claude-vision` backend when OCR-style transcription is required.

### Subscription-backed Q&A

The `ask` and local HTML Q&A commands invoke `codex exec` in an ephemeral, read-only sandbox. Install a current [Codex CLI](https://learn.chatgpt.com/docs/codex-cli), run `codex login`, and choose ChatGPT sign-in. The integration intentionally rejects API-key authentication so Q&A cannot silently switch from ChatGPT subscription access to usage-based API billing. See the official [authentication guide](https://learn.chatgpt.com/docs/auth) and [non-interactive mode reference](https://learn.chatgpt.com/docs/non-interactive-mode).

## Obsidian Integration

- Graph view is enabled for browsing the wiki structure visually.
- Dataview and Marp are included in the tracked vault configuration.
- QuickAdd and Templater are configured for structured capture workflows.
- A starter Dataview page is available at [wiki/DASHBOARD.md](wiki/DASHBOARD.md).

Relevant configuration files:

- `.obsidian/community-plugins.json`
- `.obsidian/core-plugins.json`
- `.obsidian/plugins/quickadd/data.json`
- `.obsidian/plugins/templater-obsidian/data.json`

## Public Repository Notes

- `raw/` is kept in example mode in the public repository.
- Private PDFs and other large local research assets are stored outside the repository.
- Local caches, rendered PDF page images, watcher state, and transient exports are ignored by Git.

## Acknowledgements

This project is inspired by Andrej Karpathy's LLM Wiki.
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Author

Dr. Xinyu Yang from A*STAR (yang_xinyu@a-star.edu.sg)
