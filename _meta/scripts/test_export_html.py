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

            self.assertEqual(result["pages_written"], 7)
            self.assertTrue((root / "output/html/projects/research-programme.html").is_file())
            self.assertTrue((root / "output/html/projects/research-programme-solver.html").is_file())
            self.assertTrue((root / "output/html/projects/research-programme-guardrail.html").is_file())
            home = (root / "output/html/index.html").read_text(encoding="utf-8")
            self.assertIn('id="projects"', home)
            self.assertIn("Research Automation", home)
            self.assertIn('href="projects/research-programme.html"', home)
            self.assertIn('class="home-project-row is-subproject"', home)
            self.assertIn("RESEARCH-PROGRAMME SUBPROJECT", home)
            self.assertIn("COMPLETED · RESEARCH-PROGRAMME SUBPROJECT", home)
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


if __name__ == "__main__":
    unittest.main()
