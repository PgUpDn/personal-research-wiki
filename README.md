# Personal Research Wiki

Personal Research Wiki is an Obsidian-based research workspace for collecting raw source material, compiling it into a linked markdown knowledge base, and querying that knowledge base through LLM-assisted workflows.

The repository is organized around a simple idea: keep source material in `raw/`, let the compiler maintain structured knowledge in `wiki/`, and render downstream answers, slides, and reports into `output/`.

## Overview

This project tracks the research vault itself, including:

- source material in `raw/`
- compiled knowledge pages in `wiki/`
- capture and note templates in `Templates/`
- selected Obsidian configuration in `.obsidian/`
- compiler and export tooling in `_meta/`

The public version of this repository is intentionally lightweight. Large private PDFs, rendered page caches, transient outputs, and machine-specific workspace state are kept out of version control.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `raw/` | source documents, notes, and local assets managed by the user |
| `wiki/sources/` | one wiki page per source document |
| `wiki/concepts/` | synthesized concept pages spanning multiple sources |
| `wiki/derived/` | durable answers and outputs filed back into the wiki |
| `wiki/` | index, system notes, log, health checks, and derived pages |
| `output/` | generated answers, slides, charts, and reports |
| `_meta/` | compiler scripts, state, PDF caches, and export tooling |
| `Templates/` | QuickAdd and Templater templates for structured capture |

## Research Workflow

1. Add source material to `raw/`.
2. Run the compiler or watcher to convert PDFs, refresh source pages, update concept pages, and keep the wiki index current.
3. Query the compiled wiki to generate notes, comparisons, reports, or presentations.
4. File valuable outputs back into `wiki/derived/` so the knowledge base compounds over time.
5. Review `wiki/LINT_AND_HEAL.md` to identify broken links, low-coverage areas, and opportunities for refinement.

The schema and maintenance rules for the vault are documented in [AGENTS.md](AGENTS.md).

## Quick Start

Open the repository root directly in Obsidian so that `raw/`, `wiki/`, `_meta/`, and `output/` remain visible within a single vault.

Common commands:

```bash
.venv/bin/python _meta/scripts/wiki_cli.py compile --root .
.venv/bin/python _meta/scripts/wiki_cli.py watch --root . --once
.venv/bin/python _meta/scripts/wiki_cli.py search --root . "meshgraphnets"
.venv/bin/python _meta/scripts/wiki_cli.py ask --root . "What are the most common themes in the CFD papers?" --file-into-wiki
.venv/bin/python _meta/scripts/wiki_cli.py export-html --root .
```

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

This project is inspired by Andrej Karpathy's LLM Wiki workflow.

## Contact

Dr. Xinyu Yang  
`yang_xinyu@a-star.edu.sg`
