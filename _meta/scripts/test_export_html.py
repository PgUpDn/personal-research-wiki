#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

import export_html


class ProjectExportTest(unittest.TestCase):
    def test_home_uses_complete_pdf_filename_for_truncated_uppercase_title(self) -> None:
        doc = {
            "title": "CACHE-TO-CACHE: DIRECT SEMANTIC COMMUNICA",
            "text": (
                "---\n"
                "sources:\n"
                '  - "raw/zotero/AI/Fu et al. - 2026 - Cache-to-Cache Direct Semantic Communication Between Large Language Models.pdf"\n'
                "---\n"
            ),
        }
        self.assertEqual(
            export_html.home_source_title(doc),
            "Cache-to-Cache Direct Semantic Communication Between Large Language Models",
        )

    def test_project_page_is_exported_and_featured_on_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/projects").mkdir(parents=True)
            (root / "wiki/INDEX.md").write_text(
                "# Research Wiki Index\n\n- Last compiled: 2026-08-03\n",
                encoding="utf-8",
            )
            (root / "wiki/projects/research-programme.md").write_text(
                "---\n"
                'title: "Research Automation Programme"\n'
                'note_type: "project"\n'
                'project_id: "research-programme"\n'
                'project_name: "Research Automation"\n'
                'project_status: "active"\n'
                "snapshot_date: 2026-07-30\n"
                "---\n\n"
                "# Research Automation Programme\n\n"
                "A trustworthy scientific system with evidence-backed milestones.\n",
                encoding="utf-8",
            )
            (root / "wiki/projects/research-programme-solver.md").write_text(
                "---\n"
                'title: "Solver Executor"\n'
                'note_type: "project"\n'
                'project_id: "solver"\n'
                'project_name: "Solver"\n'
                'project_level: "subproject"\n'
                'parent_project_id: "research-programme"\n'
                'project_status: "active"\n'
                "snapshot_date: 2026-08-05\n"
                "---\n\n"
                "# Solver Executor\n\n"
                "A differentiable executor under the research programme.\n",
                encoding="utf-8",
            )
            (root / "wiki/projects/research-programme-guardrail.md").write_text(
                "---\n"
                'title: "Workflow Guardrail"\n'
                'note_type: "project"\n'
                'project_id: "guardrail"\n'
                'project_name: "Guardrail"\n'
                'project_level: "subproject"\n'
                'parent_project_id: "research-programme"\n'
                'project_status: "completed"\n'
                "snapshot_date: 2026-07-30\n"
                "---\n\n"
                "# Workflow Guardrail\n\n"
                "A completed scientific workflow guardrail.\n",
                encoding="utf-8",
            )

            result = export_html.export_html(root)

            self.assertEqual(result["pages_written"], 8)
            self.assertTrue(result["okf_conformant"])
            self.assertTrue((root / "output/html/projects/research-programme.html").is_file())
            self.assertTrue((root / "output/html/projects/research-programme-solver.html").is_file())
            self.assertTrue((root / "output/html/projects/research-programme-guardrail.html").is_file())
            home = (root / "output/html/index.html").read_text(encoding="utf-8")
            self.assertIn('id="projects"', home)
            self.assertIn("Research Automation", home)
            self.assertIn('href="projects/research-programme.html"', home)
            self.assertIn('class="home-project-group"', home)
            self.assertIn('class="home-subproject-row"', home)
            self.assertIn("<small>Completed</small>", home)
            search_index = json.loads(
                (root / "output/html/assets/search-index.json").read_text(encoding="utf-8")
            )
            project = next(
                item for item in search_index["documents"] if item["project_id"] == "research-programme"
            )
            self.assertEqual(project["group"], "Projects")
            self.assertEqual(project["project_status"], "active")
            subproject = next(item for item in search_index["documents"] if item["project_id"] == "solver")
            self.assertEqual(subproject["project_level"], "subproject")
            self.assertEqual(subproject["parent_project_id"], "research-programme")
            guardrail = next(item for item in search_index["documents"] if item["project_id"] == "guardrail")
            self.assertEqual(guardrail["project_status"], "completed")
            self.assertEqual(guardrail["parent_project_id"], "research-programme")
            ask_page = (root / "output/html/ask.html").read_text(encoding="utf-8")
            self.assertIn("redirectFilePageToServer", ask_page)
            self.assertIn("mode: 'no-cors'", ask_page)
            self.assertIn("window.location.replace(localServerUrl)", ask_page)
            self.assertIn('data-file-into-wiki type="checkbox" checked', ask_page)
            knowledge = (root / "output/html/knowledge.html").read_text(encoding="utf-8")
            self.assertIn("Knowledge Map", knowledge)
            self.assertIn('data-knowledge-canvas', knowledge)
            self.assertIn("Open Knowledge Format · v0.2", knowledge)
            self.assertTrue((root / "output/html/assets/research-wiki-okf.zip").is_file())
            self.assertTrue((root / "output/html/assets/okf-manifest.json").is_file())


class MarkdownAssetExportTest(unittest.TestCase):
    def test_angle_wrapped_local_markdown_link_is_copied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/sources").mkdir(parents=True)
            (root / "wiki/INDEX.md").write_text("# Research Wiki Index\n", encoding="utf-8")
            cache = root / "_meta/converted_sources/_sanitized_clippings/example/Example Article.md"
            cache.parent.mkdir(parents=True)
            cache.write_text("# Clean article\n", encoding="utf-8")
            (root / "wiki/sources/example.md").write_text(
                "---\n"
                'title: "Example Article"\n'
                'note_type: "source"\n'
                "---\n\n"
                "[Open clean copy](<../../_meta/converted_sources/_sanitized_clippings/example/Example Article.md>)\n",
                encoding="utf-8",
            )

            export_html.export_html(root)

            exported = (root / "output/html/sources/example.html").read_text(encoding="utf-8")
            self.assertIn(
                'href="../_files/_meta/converted_sources/_sanitized_clippings/example/Example Article.md"',
                exported,
            )
            self.assertNotIn("&amp;lt;", exported)
            self.assertTrue(
                (
                    root
                    / "output/html/_files/_meta/converted_sources/_sanitized_clippings/example/Example Article.md"
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()
