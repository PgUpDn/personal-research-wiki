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
.venv/bin/python _meta/scripts/wiki_cli.py zotero-import --root . --list-collections
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

### Clipping Mermaid reconstruction

Obsidian Web Clipper captures are immutable inputs. When a clipping contains a rendered Mermaid CSS/SVG artifact, the compiler can replace it in a generated reading copy under `_meta/converted_sources/_sanitized_clippings/<source-hash>/` while leaving the file in `Clippings/` unchanged. The separate, hashed namespace prevents a same-stem clipping PDF and Markdown file from sharing a cache. Ordinary code fences and surrounding article text are preserved.

The default workflow is offline. Add recovered Mermaid definitions to the ignored local file `_meta/clipping_mermaid_sources.json`, keyed by the clipping's `source` URL and in document order:

```json
{
  "https://example.com/article": [
    "flowchart TD\n  A --> B",
    "mindmap\n  root((Topic))"
  ]
}
```

A cache is generated only when the number of valid definitions exactly matches the number of recognized render artifacts. The cache records digests of both the clipping and Mermaid definitions, so either change invalidates it. The mapping, sanitized caches, and site-specific clipper templates are ignored and are not part of the public framework.

Compilation never fetches the clipping's source URL. Inspect or export the Mermaid definitions separately, then place them in the local mapping. This keeps compilation offline and deterministic, avoids disclosing private URLs, and preserves the original clipping whenever recovery is incomplete.

### Zotero connection

The Zotero connector reads the local `zotero.sqlite` database in SQLite read-only mode and copies PDF attachments from one selected collection into `raw/zotero/<collection>/`. It never writes to Zotero. Imported PDFs, local import summaries, conversion caches, and newly created compiled pages are covered by the repository's privacy-oriented ignore rules. Because the compiler can still update already tracked example pages, stage framework files explicitly rather than using `git add -A`.

List collections, preview an import without writing anything, then import and compile:

```bash
.venv/bin/python _meta/scripts/wiki_cli.py zotero-import --root . --list-collections
.venv/bin/python _meta/scripts/wiki_cli.py zotero-import --root . --collection AI --include-subcollections --dry-run
.venv/bin/python _meta/scripts/wiki_cli.py zotero-import --root . --collection AI --include-subcollections
.venv/bin/python _meta/scripts/wiki_cli.py compile --root .
```

The default [Zotero data directory](https://www.zotero.org/support/zotero_data) is `~/Zotero`; override it with `--zotero-data-dir`, or pass a database explicitly with `--database`. Collection names are case-insensitive. If a name occurs in more than one Zotero library, add `--library-id` or select its collection key with `--collection-key`. Subcollections are included only when `--include-subcollections` is present.

[Stored and linked attachments](https://www.zotero.org/support/attaching_files) are supported, including standalone PDF attachments filed directly in a collection. Stored attachments are resolved below Zotero's `storage/` directory. For Zotero paths beginning with `attachments:`, provide the linked-file base directory with `--linked-base-dir`. Make sure attachment files are available locally before importing. The importer de-duplicates exact PDF content by SHA-256, verifies every copy, writes only a redacted summary under `_meta/zotero_imports/`, and treats `--dry-run` as a strict no-write operation. Run the watcher instead of the final `compile` command if you want future Zotero imports compiled automatically.

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
