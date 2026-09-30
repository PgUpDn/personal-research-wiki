#!/usr/bin/env python3
"""Curated concept notes: wiki/curated/<slug>.md fragments that survive compile.

Covers the convention documented in wiki/PAGE_FORMATS.md ("Curated Concept Notes"):
- a catalog slug with a curated file and zero matching sources is still generated,
  with the curated body inlined as `## Curated notes` right after `## Definition`;
- a concept with neither sources nor a curated file is still deleted as stale;
- `keep_without_sources` in the catalog pins a concept without a curated file;
- the curated fragment never shows up as a standalone page (INDEX, lint, exports, search).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

import wiki_pipeline

CURATED_SLUG = "visual-pair-review-harness"
UNCURATED_SLUG = "neural-operators"
CURATED_TITLE = "Visual-Pair Review Harness (curated notes)"
ITALIC_LINE = f"*Hand-maintained in wiki/curated/{CURATED_SLUG}.md; the other sections are compiler output.*"

CURATED_TEXT = (
    "---\n"
    f'title: "{CURATED_TITLE}"\n'
    'note_type: "curated"\n'
    f'concept: "{CURATED_SLUG}"\n'
    "sources:\n"
    '  - "raw/cad2struct/VISUAL_PAIR_REVIEW_HARNESS_2026-09-05_EN.md"\n'
    "---\n"
    "\n"
    f"# {CURATED_TITLE}\n"
    "\n"
    "### The eight-step method\n"
    "\n"
    "1. Same window, same scale; an instance of [[Harness Engineering]].\n"
    "2. Verify the instrument numerically before comparing anything.\n"
    "\n"
    "### Limits\n"
    "\n"
    "- Comparators stall on tall images; see [[Engineering Drawing Understanding|drawing understanding]].\n"
)

NEURAL_OPERATOR_NOTE = (
    "# Neural operators for parametric PDE families\n"
    "\n"
    "Neural operators such as the Fourier neural operator learn solution operators for whole families "
    "of partial differential equations instead of predicting a single state at a time. A neural operator "
    "trained on one resolution can be evaluated on another, which is why neural operators are used as "
    "surrogate models in simulation acceleration.\n"
)


def make_vault(tmp: str) -> Path:
    root = Path(tmp)
    (root / "raw").mkdir()
    (root / "wiki/concepts").mkdir(parents=True)
    (root / "wiki/curated").mkdir(parents=True)
    return root


def write_curated(root: Path, slug: str = CURATED_SLUG, text: str = CURATED_TEXT) -> Path:
    path = root / "wiki/curated" / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return path


class CuratedConceptCompileTest(unittest.TestCase):
    def test_curated_concept_with_zero_sources_is_generated_with_curated_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            write_curated(root)

            result = wiki_pipeline.compile_wiki(root)

            page = root / "wiki/concepts" / f"{CURATED_SLUG}.md"
            self.assertTrue(page.exists(), "curated concept must be generated without any matching source")
            text = page.read_text(encoding="utf-8")
            self.assertIn("source_count: 0", text)
            self.assertIn(f'curated_note: "wiki/curated/{CURATED_SLUG}.md"', text)
            self.assertIn('note_type: "concept"', text)
            self.assertNotIn('note_type: "curated"', text)
            self.assertIn("## Curated notes", text)
            self.assertIn(ITALIC_LINE, text)
            self.assertIn("- Representative sources: none matched yet.", text)
            # curated body inlined verbatim, wikilinks (including aliased ones) untouched
            self.assertIn("1. Same window, same scale; an instance of [[Harness Engineering]].", text)
            self.assertIn("[[Engineering Drawing Understanding|drawing understanding]]", text)
            self.assertIn("### The eight-step method", text)
            # curated frontmatter and leading H1 are stripped
            self.assertNotIn(f"# {CURATED_TITLE}", text)
            self.assertNotIn(f'concept: "{CURATED_SLUG}"', text)
            # placement: Definition -> Curated notes -> What The Sources Emphasize
            self.assertLess(text.index("## Definition"), text.index("## Curated notes"))
            self.assertLess(text.index("## Curated notes"), text.index("## What The Sources Emphasize"))
            self.assertLess(text.index(ITALIC_LINE), text.index("### The eight-step method"))
            self.assertIn(CURATED_SLUG, result["pinned_concepts"])
            self.assertIn(CURATED_SLUG, result["curated_concepts"])
            self.assertEqual(result["concept_count"], 1)

            state = wiki_pipeline.load_state(root)
            self.assertEqual(state["concepts"][CURATED_SLUG]["source_count"], 0)
            self.assertEqual(state["concepts"][CURATED_SLUG]["curated_note"], f"wiki/curated/{CURATED_SLUG}.md")

            # a second compile must never delete the pinned page as stale
            second = wiki_pipeline.compile_wiki(root)
            self.assertTrue(page.exists())
            self.assertNotIn(f"wiki/concepts/{CURATED_SLUG}.md", second["removed_articles"])
            self.assertEqual(second["written_articles"], [])

    def test_concept_without_sources_or_curated_file_is_still_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            stale_catalog_page = root / "wiki/concepts" / f"{UNCURATED_SLUG}.md"
            stale_catalog_page.write_text("# Neural Operators\n\nHand-written prose that must not survive.\n", encoding="utf-8")
            stale_unknown_page = root / "wiki/concepts/not-in-catalog.md"
            stale_unknown_page.write_text("# Unknown\n", encoding="utf-8")

            result = wiki_pipeline.compile_wiki(root)

            self.assertFalse(stale_catalog_page.exists())
            self.assertFalse(stale_unknown_page.exists())
            self.assertIn(f"wiki/concepts/{UNCURATED_SLUG}.md", result["removed_articles"])
            self.assertIn("wiki/concepts/not-in-catalog.md", result["removed_articles"])
            self.assertEqual(result["pinned_concepts"], [])
            self.assertEqual(result["concept_count"], 0)

    def test_keep_without_sources_pins_a_concept_without_curated_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            with mock.patch.dict(wiki_pipeline.CONCEPTS_BY_SLUG[UNCURATED_SLUG], {"keep_without_sources": True}):
                result = wiki_pipeline.compile_wiki(root)

            page = root / "wiki/concepts" / f"{UNCURATED_SLUG}.md"
            self.assertTrue(page.exists())
            text = page.read_text(encoding="utf-8")
            self.assertIn("source_count: 0", text)
            self.assertIn("- Representative sources: none matched yet.", text)
            self.assertNotIn("## Curated notes", text)
            self.assertNotIn("curated_note:", text)
            self.assertEqual(result["pinned_concepts"], [UNCURATED_SLUG])
            self.assertEqual(result["curated_concepts"], [])

    def test_source_backed_concept_without_curated_file_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            (root / "raw/neural-operators.md").write_text(NEURAL_OPERATOR_NOTE, encoding="utf-8")

            result = wiki_pipeline.compile_wiki(root)

            page = root / "wiki/concepts" / f"{UNCURATED_SLUG}.md"
            self.assertTrue(page.exists())
            text = page.read_text(encoding="utf-8")
            self.assertIn("source_count: 1", text)
            self.assertNotIn("## Curated notes", text)
            self.assertNotIn("curated_note:", text)
            self.assertNotIn("none matched yet", text)
            self.assertIn("appears across `raw/` as", text)
            self.assertNotIn(UNCURATED_SLUG, result["pinned_concepts"])

    def test_source_backed_concept_with_curated_file_keeps_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            (root / "raw/neural-operators.md").write_text(NEURAL_OPERATOR_NOTE, encoding="utf-8")
            write_curated(root, slug=UNCURATED_SLUG, text=CURATED_TEXT.replace(CURATED_SLUG, UNCURATED_SLUG))

            result = wiki_pipeline.compile_wiki(root)

            text = (root / "wiki/concepts" / f"{UNCURATED_SLUG}.md").read_text(encoding="utf-8")
            self.assertIn("source_count: 1", text)
            self.assertIn("## Curated notes", text)
            self.assertIn(f"*Hand-maintained in wiki/curated/{UNCURATED_SLUG}.md; the other sections are compiler output.*", text)
            self.assertIn("from `raw/neural-operators.md`", text)
            self.assertNotIn("none matched yet", text)
            self.assertNotIn(UNCURATED_SLUG, result["pinned_concepts"])
            self.assertIn(UNCURATED_SLUG, result["curated_concepts"])


class CuratedFragmentIsNotAPageTest(unittest.TestCase):
    def test_curated_fragment_is_absent_from_index_lint_exports_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(tmp)
            curated_path = write_curated(root)

            result = wiki_pipeline.compile_wiki(root)

            index_text = (root / "wiki/INDEX.md").read_text(encoding="utf-8")
            self.assertIn(f"concepts/{CURATED_SLUG}.md", index_text)
            self.assertNotIn("curated/", index_text)
            self.assertNotIn(CURATED_TITLE, index_text)

            lint_report = (root / result["lint"]["report"]).read_text(encoding="utf-8")
            self.assertNotIn("wiki/curated", lint_report)
            self.assertTrue(wiki_pipeline.is_curated_fragment(CURATED_TEXT))
            self.assertFalse(wiki_pipeline.is_curated_fragment("---\nnote_type: \"concept\"\n---\n# X\n"))

            curated_resolved = curated_path.resolve()

            try:
                import export_okf
            except ImportError as exc:  # pragma: no cover - optional module
                self.skipTest(f"export_okf unavailable: {exc}")
            okf_docs = {path.resolve() for path in export_okf.collect_native_documents(root)}
            self.assertNotIn(curated_resolved, okf_docs)

            try:
                import export_html
            except ImportError as exc:  # pragma: no cover - optional module
                self.skipTest(f"export_html unavailable: {exc}")
            html_docs = {path.resolve() for path in export_html.collect_export_docs(root)}
            self.assertNotIn(curated_resolved, html_docs)

            try:
                import ask_wiki
            except ImportError as exc:  # pragma: no cover - optional module
                self.skipTest(f"ask_wiki unavailable: {exc}")
            ask_docs = {doc["path"].resolve() for doc in ask_wiki.collect_wiki_documents(root)}
            self.assertNotIn(curated_resolved, ask_docs)

            try:
                import wiki_cli
            except ImportError as exc:  # pragma: no cover - optional module
                self.skipTest(f"wiki_cli unavailable: {exc}")
            search_docs = {path.resolve() for path in wiki_cli.wiki_documents(root)}
            self.assertNotIn(curated_resolved, search_docs)
            hits = wiki_cli.search_wiki(root, "eight-step method", limit=10)
            hit_paths = {hit["path"] for hit in hits["results"]}
            self.assertNotIn(f"wiki/curated/{CURATED_SLUG}.md", hit_paths)
            self.assertIn(f"wiki/concepts/{CURATED_SLUG}.md", hit_paths)

    def test_curated_note_body_strips_frontmatter_and_leading_h1_only(self) -> None:
        body = wiki_pipeline.curated_note_body(CURATED_TEXT)
        self.assertTrue(body.startswith("### The eight-step method"))
        self.assertIn("[[Harness Engineering]]", body)
        self.assertNotIn("note_type", body)
        # a fragment without frontmatter or H1 is returned as-is
        self.assertEqual(wiki_pipeline.curated_note_body("### Only body\n\ntext\n"), "### Only body\n\ntext")


if __name__ == "__main__":
    unittest.main()
