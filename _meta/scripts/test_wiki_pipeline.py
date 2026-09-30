#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pymupdf

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
    def test_pdf_author_line_before_collaboration_name(self) -> None:
        text = (
            "Discovery Foundation Models:\n"
            "Toward Open-Ended Discovery Intelligence\n"
            "Ling Yang Zhenfei Yin Yingcheng Wu\n"
            "DFM Scientist Collaboration Program\n"
            "Abstract\n"
        )
        path = Path("Yang et al. - 2026 - Discovery Foundation Models.pdf")
        self.assertEqual(
            wiki_pipeline.extract_authors(
                text,
                "Discovery Foundation Models Toward Open-Ended Discovery Intelligence",
                path,
            ),
            ["Ling Yang", "Zhenfei Yin", "Yingcheng Wu"],
        )

    def test_spacing_recovery_uses_pdftotext_only_for_fused_words(self) -> None:
        damaged = " ".join(["Foundationmodelshaveprogressedfromlearningandreasoning"] * 40)
        recovered = " ".join(["Foundation models have progressed from learning and reasoning"] * 40)
        with (
            mock.patch.object(wiki_pipeline.shutil, "which", return_value="/usr/bin/pdftotext"),
            mock.patch.object(
                wiki_pipeline.subprocess,
                "run",
                return_value=mock.Mock(returncode=0, stdout=recovered),
            ) as run,
        ):
            self.assertEqual(
                wiki_pipeline.recover_markitdown_spacing(Path("paper.pdf"), damaged),
                (recovered, "markitdown+pdftotext-spacing-recovery", "pdftotext-spacing-recovery"),
            )
            run.assert_called_once()
            self.assertEqual(
                wiki_pipeline.recover_markitdown_spacing(Path("paper.pdf"), recovered),
                (recovered, "markitdown", "markitdown"),
            )
            run.assert_called_once()

    def test_convert_pdfs_uses_markitdown_cli_when_available(self) -> None:
        previous = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                raw_dir = root / "raw"
                raw_dir.mkdir()
                pdf_path = raw_dir / "Example - 2026 - MarkItDown Test.pdf"

                document = pymupdf.open()
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

    def test_empty_markitdown_output_falls_back_to_local_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            pdf_path = raw_dir / "Example - 2026 - Scanned Paper.pdf"

            document = pymupdf.open()
            document.new_page()
            document.save(pdf_path)
            document.close()

            work_dir = root / "_meta/pdf2md_work/scanned-paper"
            work_dir.mkdir(parents=True)
            image_path = work_dir / "page-001.png"
            image_path.write_bytes(b"rendered page")

            with (
                mock.patch.object(
                    wiki_pipeline,
                    "run_markitdown",
                    side_effect=RuntimeError("MarkItDown returned empty Markdown"),
                ),
                mock.patch.object(
                    wiki_pipeline,
                    "render_pdf_pages",
                    return_value=([image_path], work_dir, "pymupdf"),
                ),
                mock.patch.object(
                    wiki_pipeline,
                    "tesseract_markdown_from_images",
                    return_value="### Page 1\n\nOCR body.",
                ),
            ):
                result = wiki_pipeline.convert_pdfs(root, force=True)

            self.assertEqual(result["failures"], [])
            cache_path = root / result["converted"][0]["cache_markdown"]
            cache_text = cache_path.read_text(encoding="utf-8")
            self.assertIn(
                'conversion_pipeline: "markitdown+pymupdf+tesseract-ocr"',
                cache_text,
            )
            self.assertIn('transcription_mode: "markitdown-ocr-fallback"', cache_text)
            self.assertIn("OCR body.", cache_text)


class MarkItDownTitleDetectionTest(unittest.TestCase):
    def test_import_collision_digest_is_not_part_of_the_paper_title(self) -> None:
        pdf_path = Path(
            "Wu et al. - 2024 - Compositional Generative Inverse Design-752b308f.pdf"
        )
        expected = "Compositional Generative Inverse Design"
        self.assertEqual(wiki_pipeline.paper_title_from_name(pdf_path.name), expected)
        self.assertEqual(
            wiki_pipeline.detect_title(
                '---\ntitle: "Compositional Generative Inverse Design-752b308f"\n---\n',
                pdf_path,
            ),
            expected,
        )

    def test_ocr_patent_title_is_recovered_from_the_document_body(self) -> None:
        pdf_path = Path("opaque-download-token.pdf")
        markdown = (
            "### Page 3\n\n"
            "WO 2026/064243 PCT/US2025/046388\n\n"
            "MACHINE LEARNING BASED VIRTUAL SENSING OF WAFER\n"
            "TEMPERATURES DURING REFLOW PROCESS IN A PHYSICAL VAPOR\n"
            "DEPOSITION CHAMBER WITH UNCERTAIN CHAMBER PHYSICAL\n"
            "PROPERTIES AND VARYING OPERATING CONDITIONS\n\n"
            "BACKGROUND\n"
        )
        self.assertEqual(
            wiki_pipeline.detect_title(markdown, pdf_path),
            "Machine learning based virtual sensing of wafer temperatures during reflow process in a physical vapor deposition chamber with uncertain chamber physical properties and varying operating conditions",
        )

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


class SourceCanonicalizationTest(unittest.TestCase):
    def test_title_equivalent_source_variants_merge_into_one_canonical_profile(self) -> None:
        profiles = {
            "Clippings/paper.md": {
                "title": "Example Scientific Paper",
                "aliases": ["Example Scientific Paper"],
                "source": "Clippings/paper.md",
                "source_files": ["Clippings/paper.md"],
                "source_kind": "raw_markdown",
                "concepts": ["ai-agents"],
                "domains": [],
                "themes": [],
                "section_index": [],
                "github_links": [],
            },
            "raw/zotero/AI/paper.pdf": {
                "title": "Example Scientific Paper-1a2b3c4d",
                "aliases": ["example2026paper"],
                "source": "raw/zotero/AI/paper.pdf",
                "source_files": ["raw/zotero/AI/paper.pdf"],
                "source_kind": "raw_pdf",
                "concepts": ["scientific-machine-learning"],
                "domains": ["agents and automation"],
                "themes": [],
                "section_index": [],
                "github_links": [],
            },
        }

        canonical, duplicates = wiki_pipeline.canonical_source_profiles(profiles)

        self.assertEqual(list(canonical), ["raw/zotero/AI/paper.pdf"])
        profile = canonical["raw/zotero/AI/paper.pdf"]
        self.assertEqual(
            profile["source_files"],
            ["Clippings/paper.md", "raw/zotero/AI/paper.pdf"],
        )
        self.assertEqual(
            profile["concepts"],
            ["ai-agents", "scientific-machine-learning"],
        )
        self.assertEqual(
            duplicates,
            {"Clippings/paper.md": "raw/zotero/AI/paper.pdf"},
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

    def test_declared_authors_drop_footnote_markers(self) -> None:
        cache = '---\ntitle: Example\nauthors:\n  - "Tung Nguyen∗"\n  - "Arsh Koneru*†"\n---\n\nBody.\n'
        self.assertEqual(
            wiki_pipeline.extract_authors(cache, "Example", Path("raw/example.pdf")),
            ["Tung Nguyen", "Arsh Koneru"],
        )

    def test_unlabeled_title_page_abstract_beats_late_abstract_verb(self) -> None:
        abstract_lines = [
            "Scientific discovery is defined by the ability to identify the boundaries of existing knowledge and",
            "venture into unexplored territory. We introduce an autonomous multi-agent framework that takes an",
            "initial problem as input, establishes baselines, formulates hypotheses and coordinates agents to",
            "run an end-to-end discovery cycle, validated by a simulated peer-review rebuttal engine at scale.",
        ]
        cache = (
            "---\ntitle: Example\nsource_kind: raw_pdf\n---\n\n"
            "## Extracted Markdown\n\n"
            "Example: Pioneering the Frontier\n"
            "JaneDoe1,JohnRoe1,AnnSmith2 and\nBobLee1\n"
            "1ExampleResearch,2UniversityofExample\n"
            + "\n".join(abstract_lines)
            + "\n1. Introduction\nScientific discovery has long been the hallmark of human ingenuity.\n"
            + "Filler text. " * 900
            + "\nabstract all stages (see Table 1) using pseudocode.\n"
        )

        abstract = wiki_pipeline.extract_abstract(cache)

        self.assertTrue(abstract.startswith("Scientific discovery is defined"))
        self.assertIn("peer-review rebuttal engine", abstract)
        self.assertNotIn("JaneDoe", abstract)

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
            document = pymupdf.open()
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
            document = pymupdf.open()
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


class ClippingSanitizationTest(unittest.TestCase):
    @staticmethod
    def rendered_mermaid_artifact() -> str:
        return (
            "#mermaid-1787117213896{font-family:trebuchet ms;}"
            "@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}"
            "#mermaid-1787117213896 .edge-animation-slow{animation:dash 50s linear infinite;}"
            "#mermaid-1787117213896 .flowchart-link{stroke-width:2px;fill:none;}"
            "#mermaid-1787117213896 .mindmap-node-label{text-anchor:middle;}"
            "#mermaid-1787117213896 :root{--mermaid-font-family:trebuchet ms;}"
            + "fill:#fff;stroke-width:1px;font-family:arial;animation:dash 20s;" * 30
        )

    def test_mermaid_sources_are_extracted_from_escaped_page_markdown(self) -> None:
        page_html = r'''<script>```mermaid\nmindmap\n  root((AI Research))\n```</script>
<script>```mermaid\nflowchart TD\n  A[\"Propose\"] --> B[\"Verify\"]\n```</script>'''

        sources = wiki_pipeline.extract_mermaid_sources_from_html(page_html)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0], "mindmap\n  root((AI Research))")
        self.assertIn('A["Propose"] --> B["Verify"]', sources[1])

    def test_only_rendered_mermaid_artifact_fences_are_reconstructed(self) -> None:
        artifact = self.rendered_mermaid_artifact()
        markdown = (
            "# Example\n\n"
            "```python\nprint('keep me')\n```\n\n"
            f"```\n{artifact}\n```\n"
        )

        reconstructed_markdown, reconstructed = wiki_pipeline.sanitize_clipping_markdown(
            markdown,
            ["flowchart TD\n  A --> B"],
        )

        self.assertEqual(reconstructed, 1)
        self.assertIn("print('keep me')", reconstructed_markdown)
        self.assertIn("```mermaid\nflowchart TD\n  A --> B\n```", reconstructed_markdown)
        self.assertNotIn("#mermaid-1787117213896", reconstructed_markdown)

    def test_local_mermaid_sources_are_available_when_article_is_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_file = root / "_meta/clipping_mermaid_sources.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                json.dumps({"https://example.com/article": ["mindmap\n  root((Recovered))"]}),
                encoding="utf-8",
            )

            sources = wiki_pipeline.local_mermaid_sources(root, "https://example.com/article")

            self.assertEqual(sources, ["mindmap\n  root((Recovered))"])

    def test_clipping_uses_generated_cache_without_modifying_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clipping_dir = root / "Clippings"
            clipping_dir.mkdir(parents=True)
            source_url = "https://example.com/article"
            artifact = self.rendered_mermaid_artifact()
            original = (
                "---\n"
                'title: "Example Article"\n'
                f'source: "{source_url}"\n'
                "---\n"
                "Readable paragraph.\n\n"
                f"```\n{artifact}\n```\n"
            )
            clipping_path = clipping_dir / "Example Article.md"
            clipping_path.write_text(original, encoding="utf-8")
            source_file = root / "_meta/clipping_mermaid_sources.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                json.dumps({source_url: ["mindmap\n  root((Recovered))"]}),
                encoding="utf-8",
            )

            record = next(
                item
                for item in wiki_pipeline.source_input_records(root)
                if item["source"] == "Clippings/Example Article.md"
            )

            self.assertEqual(clipping_path.read_text(encoding="utf-8"), original)
            self.assertEqual(record["sanitized_artifact_blocks"], 1)
            self.assertEqual(record["reconstructed_mermaid_blocks"], 1)
            self.assertEqual(
                record["content_path"],
                wiki_pipeline.converted_raw_markdown_path(root, clipping_path),
            )
            cache = record["content_path"].read_text(encoding="utf-8")
            self.assertIn('sanitization_pipeline: "clipper-mermaid-reconstruction-v2"', cache)
            self.assertIn("reconstructed_mermaid_blocks: 1", cache)
            self.assertIn("mermaid_sources_digest:", cache)
            self.assertIn("Readable paragraph.", cache)
            self.assertIn("```mermaid\nmindmap\n  root((Recovered))\n```", cache)
            self.assertNotIn("#mermaid-1787117213896", cache)
            first_digest = wiki_pipeline.frontmatter_scalar(cache, "mermaid_sources_digest")
            source_file.write_text(
                json.dumps({source_url: ["flowchart TD\n  A --> B"]}),
                encoding="utf-8",
            )
            cached_path, reconstructed = wiki_pipeline.prepared_raw_markdown_content_path(
                root,
                clipping_path,
            )
            self.assertEqual(cached_path, record["content_path"])
            self.assertEqual(reconstructed, 1)
            updated_cache = cached_path.read_text(encoding="utf-8")
            self.assertIn("```mermaid\nflowchart TD\n  A --> B\n```", updated_cache)
            self.assertNotEqual(
                first_digest,
                wiki_pipeline.frontmatter_scalar(updated_cache, "mermaid_sources_digest"),
            )

            source_file.unlink()
            original_path, reconstructed = wiki_pipeline.prepared_raw_markdown_content_path(
                root,
                clipping_path,
            )
            self.assertEqual(original_path, clipping_path)
            self.assertEqual(reconstructed, 0)

    def test_missing_local_mapping_preserves_the_original_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clipping_dir = root / "Clippings"
            clipping_dir.mkdir(parents=True)
            clipping_path = clipping_dir / "Offline.md"
            clipping_path.write_text(
                "---\n"
                'title: "Offline"\n'
                'source: "https://example.com/article"\n'
                "---\n\n"
                f"```\n{self.rendered_mermaid_artifact()}\n```\n",
                encoding="utf-8",
            )

            content_path, reconstructed = wiki_pipeline.prepared_raw_markdown_content_path(
                root,
                clipping_path,
            )

            self.assertEqual(content_path, clipping_path)
            self.assertEqual(reconstructed, 0)

    def test_local_mapping_requires_an_exact_diagram_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clipping_dir = root / "Clippings"
            clipping_dir.mkdir(parents=True)
            clipping_path = clipping_dir / "Counted.md"
            clipping_path.write_text(
                "---\n"
                'title: "Counted"\n'
                'source: "https://example.com/article"\n'
                "---\n\n"
                f"```\n{self.rendered_mermaid_artifact()}\n```\n",
                encoding="utf-8",
            )
            source_file = root / "_meta/clipping_mermaid_sources.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                json.dumps(
                    {
                        "https://example.com/article": [
                            "flowchart TD\n  A --> B",
                            "mindmap\n  root((Extra))",
                        ]
                    }
                ),
                encoding="utf-8",
            )
            content_path, reconstructed = wiki_pipeline.prepared_raw_markdown_content_path(
                root,
                clipping_path,
            )

            self.assertEqual(content_path, clipping_path)
            self.assertEqual(reconstructed, 0)

    def test_non_clipping_markdown_cannot_overwrite_pdf_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            (raw_dir / "shared.md").write_text(
                f"```\n{self.rendered_mermaid_artifact()}\n```\n",
                encoding="utf-8",
            )
            (raw_dir / "shared.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
            pdf_cache = root / "_meta/converted_sources/shared.md"
            pdf_cache.parent.mkdir(parents=True)
            pdf_cache.write_text("PDF CACHE SENTINEL\n", encoding="utf-8")

            records = wiki_pipeline.source_input_records(root)
            markdown_record = next(item for item in records if item["source"] == "raw/shared.md")

            self.assertEqual(markdown_record["content_path"], raw_dir / "shared.md")
            self.assertEqual(pdf_cache.read_text(encoding="utf-8"), "PDF CACHE SENTINEL\n")

    def test_same_stem_clipping_markdown_and_pdf_use_distinct_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clipping_dir = root / "Clippings"
            clipping_dir.mkdir()
            source_url = "https://example.com/article"
            markdown_path = clipping_dir / "shared.md"
            markdown_path.write_text(
                "---\n"
                f'source: "{source_url}"\n'
                "---\n\n"
                f"```\n{self.rendered_mermaid_artifact()}\n```\n",
                encoding="utf-8",
            )
            pdf_path = clipping_dir / "shared.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
            source_file = root / "_meta/clipping_mermaid_sources.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                json.dumps({source_url: ["flowchart TD\n  A --> B"]}),
                encoding="utf-8",
            )
            pdf_cache = wiki_pipeline.converted_pdf_markdown_path(root, pdf_path)
            pdf_cache.parent.mkdir(parents=True)
            pdf_cache.write_text("PDF CACHE SENTINEL\n", encoding="utf-8")

            records = wiki_pipeline.source_input_records(root)
            markdown_record = next(item for item in records if item["source"] == "Clippings/shared.md")

            self.assertNotEqual(markdown_record["content_path"], pdf_cache)
            self.assertIn("_sanitized_clippings", markdown_record["content_path"].parts)
            self.assertEqual(pdf_cache.read_text(encoding="utf-8"), "PDF CACHE SENTINEL\n")

    def test_same_source_url_keeps_distinct_clipping_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clipping_dir = root / "Clippings"
            clipping_dir.mkdir(parents=True)
            for name in ("Article.md", "Article annotated.md"):
                (clipping_dir / name).write_text(
                    "---\n"
                    f'title: "{Path(name).stem}"\n'
                    'source: "https://example.com/article"\n'
                    "---\n\nReadable paragraph.\n",
                    encoding="utf-8",
                )

            records = wiki_pipeline.source_input_records(root)

            self.assertEqual(
                [record["source"] for record in records],
                ["Clippings/Article annotated.md", "Clippings/Article.md"],
            )

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
