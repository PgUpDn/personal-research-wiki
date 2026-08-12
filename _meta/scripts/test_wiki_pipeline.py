#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fitz

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

import wiki_pipeline

from wiki_pipeline import load_claude_api_key


class ClaudeApiKeyLoadingTest(unittest.TestCase):
    def test_load_claude_api_key_strips_fullwidth_colon_prefix(self) -> None:
        previous = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "ANTHROPIC_API_KEY：test-api-key"
        try:
            self.assertEqual(load_claude_api_key(Path(".").resolve()), "test-api-key")
        finally:
            if previous is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = previous


class MarkItDownPdfConversionTest(unittest.TestCase):
    def test_convert_pdfs_uses_markitdown_cli_when_available(self) -> None:
        previous = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                raw_dir = root / "raw"
                raw_dir.mkdir()
                pdf_path = raw_dir / "Example - 2026 - MarkItDown Test.pdf"

                document = fitz.open()
                page = document.new_page()
                page.insert_text((72, 72), "MarkItDown Test")
                document.save(pdf_path)
                document.close()

                cli_path = root / "_meta/markitdown_env/bin/markitdown"
                cli_path.parent.mkdir(parents=True)
                cli_path.write_text(
                    "#!/bin/sh\n"
                    "out=''\n"
                    "while [ \"$#\" -gt 0 ]; do\n"
                    "  if [ \"$1\" = '-o' ]; then shift; out=\"$1\"; fi\n"
                    "  shift\n"
                    "done\n"
                    "printf '# MarkItDown Test\\n\\nBody from MarkItDown.\\n' > \"$out\"\n",
                    encoding="utf-8",
                )
                cli_path.chmod(0o755)

                result = wiki_pipeline.convert_pdfs(root, force=True)

                self.assertEqual(result["failures"], [])
                self.assertEqual(len(result["converted"]), 1)
                cache_path = root / result["converted"][0]["cache_markdown"]
                cache_text = cache_path.read_text(encoding="utf-8")
                self.assertIn("conversion_pipeline: \"markitdown\"", cache_text)
                self.assertIn("Body from MarkItDown.", cache_text)
        finally:
            if previous is not None:
                os.environ["ANTHROPIC_API_KEY"] = previous


class MarkItDownTitleDetectionTest(unittest.TestCase):
    def test_table_shaped_title_falls_back_to_pdf_filename(self) -> None:
        pdf_path = Path(
            "Veličković et al. - 2018 - Graph Attention Networks.pdf"
        )
        markdown = (
            "| PublishedasaconferencepaperatICLR2018 | GRAPH | ATTENTION | NETWORKS |\n"
            "| --- | --- | --- | --- |\n"
        )
        self.assertEqual(
            wiki_pipeline.detect_title(markdown, pdf_path),
            "Graph Attention Networks",
        )

    def test_truncated_title_falls_back_to_more_complete_pdf_filename(self) -> None:
        pdf_path = Path(
            "Chen et al. - 2025 - EqCollide Equivariant and Collision-Aware Deformable Objects Neural Simulator.pdf"
        )
        self.assertEqual(
            wiki_pipeline.detect_title(
                "# EqCollide: Equivariant and Collision-Aware\n",
                pdf_path,
            ),
            "EqCollide Equivariant and Collision-Aware Deformable Objects Neural Simulator",
        )

    def test_sentence_like_title_falls_back_to_shorter_pdf_filename(self) -> None:
        pdf_path = Path(
            "Yu and Yang - 2026 - Evolutionary Ensemble of Agents.pdf"
        )
        markdown = (
            "to LLM. (b) Coding Agent. A modern coding agent operates on a full code "
            "Evolutionary Ensemble (this work). A decentralized ensemble of coding\n"
        )
        self.assertEqual(
            wiki_pipeline.detect_title(markdown, pdf_path),
            "Evolutionary Ensemble of Agents",
        )


class PandocLatexConversionTest(unittest.TestCase):
    def test_ai4x_metadata_commands_are_extracted(self) -> None:
        tex = (
            "\\IACpaperyear{2026}\n"
            "\\icmlauthor{Ada Lovelace}{Example Lab}{}{}\n"
            "\\icmlauthor{Grace Hopper}{Example Lab}{}{}\n"
        )

        self.assertEqual(wiki_pipeline.extract_latex_year(tex), "2026")
        self.assertEqual(
            wiki_pipeline.extract_latex_authors(tex),
            ["Ada Lovelace", "Grace Hopper"],
        )

    def test_source_profile_uses_year_from_latex_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logical_path = root / "raw/project/example.tex"
            logical_path.parent.mkdir(parents=True)
            logical_path.write_text("\\documentclass{article}\n", encoding="utf-8")
            cache_path = root / "_meta/converted_sources/project/example.md"
            cache_path.parent.mkdir(parents=True)
            cache_path.write_text(
                "---\n"
                'title: "Example Manuscript"\n'
                "source_kind: raw_tex\n"
                "year: 2026\n"
                "authors:\n"
                '  - "Ada Lovelace"\n'
                "---\n\n"
                "## Abstract\n\nA source-native abstract.\n",
                encoding="utf-8",
            )

            profile = wiki_pipeline.build_source_profile(root, logical_path, cache_path, "raw_tex")

            self.assertEqual(profile["year"], 2026)
            self.assertEqual(profile["lead_author"], "Ada Lovelace")
            self.assertEqual(profile["citation_key"], "lovelace2026example")

    def test_supplementary_page_does_not_claim_main_title_alias(self) -> None:
        title = "Mechanistic Fidelity in Scientific Models - Supplementary Information"
        aliases = wiki_pipeline.source_page_aliases(title, "lovelace2026mechanistic-supplement")

        self.assertNotIn("Mechanistic Fidelity in Scientific Models", aliases)
        self.assertIn("lovelace2026mechanistic-supplement", aliases)

    def test_extract_abstract_reads_latex_cache_section(self) -> None:
        cache = (
            "---\n"
            "title: Example\n"
            "source_kind: raw_tex\n"
            "---\n\n"
            "## Abstract\n\n"
            "A source-native abstract with enough detail to summarize the manuscript.\n\n"
            "## Extracted Markdown\n\n"
            "# Results\n\nLong body.\n"
        )
        self.assertEqual(
            wiki_pipeline.extract_abstract(cache),
            "A source-native abstract with enough detail to summarize the manuscript.",
        )

    def test_latex_cache_without_abstract_uses_introduction(self) -> None:
        cache = (
            "---\n"
            'title: "Example Solver"\n'
            "source_kind: raw_tex\n"
            "---\n\n"
            "## Extracted Markdown\n\n"
            "# Introduction\n\n"
            "The introduction explains the differentiable physical solver and its intended role.\n\n"
            "# Methodology\n\n"
            "This section compares three architectures.\n"
        )

        self.assertEqual(
            wiki_pipeline.extract_abstract(cache),
            "The introduction explains the differentiable physical solver and its intended role.",
        )

    def test_adjacent_tex_is_indexed_instead_of_duplicate_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "raw/project"
            source_dir.mkdir(parents=True)
            tex_path = source_dir / "Lovelace - 2026 - LaTeX Source Wins.tex"
            tex_path.write_text(
                "\\documentclass{article}\n"
                "\\title{LaTeX Source Wins}\n"
                "\\author{Ada Lovelace}\n"
                "\\begin{document}\n"
                "\\maketitle\n"
                "\\input{dependency}\n"
                "\\section{Results}\n"
                "Source-native body.\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            (source_dir / "dependency.tex").write_text("Tracked dependency.\n", encoding="utf-8")

            pdf_path = tex_path.with_suffix(".pdf")
            document = fitz.open()
            document.new_page().insert_text((72, 72), "Visual snapshot")
            document.save(pdf_path)
            document.close()

            fake_pandoc = root / "fake-pandoc"
            fake_pandoc.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' '---' 'title: LaTeX Source Wins' '---' '# Results' '' 'Source-native body.'\n",
                encoding="utf-8",
            )
            fake_pandoc.chmod(0o755)

            with mock.patch.object(wiki_pipeline, "resolve_pandoc_bin", return_value=str(fake_pandoc)):
                result = wiki_pipeline.convert_tex_sources(root, force=True)

            self.assertEqual(result["failures"], [])
            self.assertEqual(len(result["converted"]), 1)
            self.assertEqual(wiki_pipeline.raw_pdf_files(root), [])
            records = wiki_pipeline.source_input_records(root)
            self.assertEqual([record["source_kind"] for record in records], ["raw_tex"])
            primary_record = next(record for record in records if record["logical_path"] == tex_path)
            cache_text = primary_record["content_path"].read_text(encoding="utf-8")
            self.assertIn('conversion_pipeline: "pandoc-latex-to-markdown"', cache_text)
            self.assertIn("dependency.tex", cache_text)

    def test_unreferenced_pdf_beside_tex_remains_a_pdf_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "raw/project"
            source_dir.mkdir(parents=True)
            (source_dir / "main.tex").write_text(
                "\\documentclass{article}\n\\begin{document}Example.\\end{document}\n",
                encoding="utf-8",
            )
            unrelated_pdf = source_dir / "unrelated.pdf"
            document = fitz.open()
            document.new_page().insert_text((72, 72), "Independent source")
            document.save(unrelated_pdf)
            document.close()

            self.assertEqual(wiki_pipeline.raw_pdf_files(root), [unrelated_pdf])


class ProjectCatalogTest(unittest.TestCase):
    def test_completed_subprojects_keep_their_parent_grouping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects_dir = root / "wiki/projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "research-programme.md").write_text(
                "---\n"
                'title: "Research Programme"\n'
                'note_type: "project"\n'
                'project_id: "research-programme"\n'
                'project_status: "active"\n'
                "---\n\n"
                "# Research Programme\n\nParent programme.\n",
                encoding="utf-8",
            )
            (projects_dir / "research-programme-guardrail.md").write_text(
                "---\n"
                'title: "Workflow Guardrail"\n'
                'note_type: "project"\n'
                'project_id: "guardrail"\n'
                'project_level: "subproject"\n'
                'parent_project_id: "research-programme"\n'
                'project_status: "completed"\n'
                "---\n\n"
                "# Workflow Guardrail\n\nCompleted guardrail work.\n",
                encoding="utf-8",
            )

            catalog = wiki_pipeline.render_projects_home(root, "2026-08-06")

            self.assertIn("## Completed Subprojects", catalog)
            self.assertIn("[[Workflow Guardrail]]", catalog)
            self.assertIn("Part of [[Research Programme]]", catalog)
            self.assertNotIn("## Other Projects", catalog)


class CompileCommandTest(unittest.TestCase):
    def test_compile_returns_failure_when_conversion_fails(self) -> None:
        conversion = {
            "converted": [],
            "archived": [],
            "failures": [{"source_pdf": "raw/scanned.pdf", "error": "empty Markdown"}],
            "pdf_converted": 0,
            "tex_converted": 0,
        }
        compiled = {
            "changed_sources": [],
            "written_source_pages": [],
            "written_articles": [],
        }
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(wiki_pipeline, "convert_sources", return_value=conversion),
            mock.patch.object(wiki_pipeline, "compile_wiki", return_value=compiled),
            mock.patch.object(wiki_pipeline, "append_log_entry"),
            mock.patch("builtins.print") as mocked_print,
        ):
            exit_code = wiki_pipeline.compile_main(["--root", tmp])

        self.assertEqual(exit_code, 1)
        rendered = mocked_print.call_args.args[0]
        self.assertIn('"conversion"', rendered)
        self.assertIn("empty Markdown", rendered)


if __name__ == "__main__":
    unittest.main()
