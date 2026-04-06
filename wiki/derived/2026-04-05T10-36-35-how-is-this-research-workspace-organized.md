---
title: "How is this research workspace organized?"
generated_at: 2026-04-05
context_mode: "full-wiki"
context_files:
  - "wiki/INDEX.md"
  - "wiki/SYSTEM_OVERVIEW.md"
  - "wiki/LINT_AND_HEAL.md"
  - "wiki/derived/README.md"
---

# How is this research workspace organized?

## Answer

The research workspace is organized as follows:

1. **Raw source material**: The `raw/` directory stores all the source documents and local images that are the input to the research process.
2. **Compiled wiki**: The `wiki/` directory contains the maintained wiki, which includes:
   - The `INDEX.md` file that provides an overview of the research workspace.
   - The `SYSTEM_OVERVIEW.md` file that describes the main pipeline and supporting infrastructure.
   - The `LINT_AND_HEAL.md` file that tracks the health of the wiki, including broken links, sparse concepts, and sources needing better coverage.
   - The `derived/README.md` file that explains how valuable query results are filed back into the wiki.
3. **Output artifacts**: The `output/` directory is where generated answers, slide decks, charts, and other reports are stored.
4. **Metadata and tooling**: The `_meta/` directory contains the compiler state, scripts, tools, and watcher infrastructure that power the research workspace.

The workflow involves:
1. Ingesting source materials into the `raw/` directory.
2. Letting the compiler keep the `wiki/` directory up to date.
3. Asking questions through the CLI and rendering results back into markdown in the `wiki/derived/` directory.
4. Running regular lint passes to ensure the wiki stays healthy and improves over time.

## Evidence

This information is directly stated in the provided wiki context:

- [[System Overview]] describes the main pipeline and directory structure.
- [[Lint + Heal]] explains the health checks performed on the wiki.
- [[Derived Notes]] outlines the purpose of the `wiki/derived/` directory.

## Open Questions

The provided context does not mention any open questions about the organization of the research workspace.
