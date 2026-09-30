#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

import export_okf


class OkfExportTest(unittest.TestCase):
    def test_exports_portable_bundle_with_provenance_and_standard_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            (root / "wiki/sources").mkdir(parents=True)
            (root / "wiki/concepts").mkdir(parents=True)
            (root / "wiki/projects").mkdir(parents=True)
            (root / "wiki/derived").mkdir(parents=True)
            (root / "raw/paper.pdf").write_bytes(b"paper")
            (root / "AGENTS.md").write_text(
                "# Schema\n\nUse inline examples such as `[[wiki-links]]` without turning them into graph edges.\n",
                encoding="utf-8",
            )
            (root / "wiki/INDEX.md").write_text("# Index\n", encoding="utf-8")
            (root / "wiki/LOG.md").write_text(
                "# Wiki Log\n\n## [2026-01-02T10:00:00] compile | Refreshed source pages\n",
                encoding="utf-8",
            )
            (root / "wiki/sources/source-a.md").write_text(
                "---\n"
                'title: "Source A"\n'
                'note_type: "source"\n'
                'source_id: "source-a"\n'
                'source_status: "compiled"\n'
                'lead_author: "Ada Lovelace"\n'
                'okf_verified_by: "human:researcher"\n'
                'okf_verified_at: "2026-01-02T10:00:00Z"\n'
                "sources:\n"
                '  - "raw/paper.pdf"\n'
                "tags:\n"
                '  - "research/source"\n'
                "---\n\n"
                "# Source A\n\n## TL;DR\n\nA compact account of the source.\n",
                encoding="utf-8",
            )
            (root / "wiki/concepts/concept-a.md").write_text(
                "---\n"
                'title: "Concept A"\n'
                'note_type: "concept"\n'
                "sources:\n"
                '  - "raw/paper.pdf"\n'
                "---\n\n"
                "# Concept A\n\n## Definition\n\nConcept A is grounded in [[Source A]].\n",
                encoding="utf-8",
            )
            (root / "wiki/projects/project-a.md").write_text(
                "---\n"
                'title: "Project A"\n'
                'note_type: "project"\n'
                'project_id: "project-a"\n'
                'project_status: "active"\n'
                "snapshot_date: 2099-01-01\n"
                "sources:\n"
                '  - "[[Concept A]]"\n'
                "---\n\n"
                "# Project A\n\n## Project Thesis\n\nA current research project.\n",
                encoding="utf-8",
            )
            (root / "wiki/derived/answer.md").write_text(
                "---\n"
                'title: "Answer A"\n'
                "context_files:\n"
                '  - "wiki/concepts/concept-a.md"\n'
                "---\n\n"
                "# Answer A\n\n## Answer\n\nA durable synthesis of [[Concept A]].\n",
                encoding="utf-8",
            )

            result = export_okf.export_okf(root)

            self.assertTrue(result["conformance"]["valid"])
            self.assertEqual(result["conformance"]["warnings"], [])
            self.assertEqual(result["documents"], 5)
            self.assertTrue((root / "output/research-wiki-okf.zip").is_file())

            root_index = (root / "output/okf/index.md").read_text(encoding="utf-8")
            self.assertIn('okf_version: "0.2"', root_index)
            self.assertIn("[Projects](projects/)", root_index)
            self.assertTrue((root / "output/okf/concepts/index.md").is_file())

            source = (root / "output/okf/sources/source-a.md").read_text(encoding="utf-8")
            self.assertIn('type: "Research Source"', source)
            self.assertIn('generated: {"by":"process:research-wiki-compiler"', source)
            self.assertIn('verified: {"by":"human:researcher","at":"2026-01-02T10:00:00Z"}', source)
            self.assertIn('"author":"human:ada-lovelace"', source)
            self.assertIn('resource: "../../../raw/paper.pdf"', source)

            concept = (root / "output/okf/concepts/concept-a.md").read_text(encoding="utf-8")
            self.assertIn('"resource":"/sources/source-a.md"', concept)
            self.assertIn("[Source A](/sources/source-a.md)", concept)
            schema = (root / "output/okf/system/schema.md").read_text(encoding="utf-8")
            self.assertIn("`[[wiki-links]]`", schema)
            self.assertNotIn("/unresolved/wiki-links.md", schema)

            project = (root / "output/okf/projects/project-a.md").read_text(encoding="utf-8")
            self.assertIn('stale_after: "2099-04-01T00:00:00Z"', project)
            derived = (root / "output/okf/derived/answer.md").read_text(encoding="utf-8")
            self.assertIn('status: "draft"', derived)
            self.assertIn('"resource":"/concepts/concept-a.md"', derived)

            manifest = json.loads((root / "output/okf/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["documents"], 5)
            self.assertEqual(manifest["summary"]["trust"]["human_reviewed"], 1)
            self.assertEqual(manifest["summary"]["trust"]["unverified"], 4)
            self.assertIn(
                {"source": "concepts/concept-a", "target": "sources/source-a", "kind": "source"},
                manifest["relationships"],
            )
            self.assertIn(
                {"source": "concepts/concept-a", "target": "sources/source-a", "kind": "link"},
                manifest["relationships"],
            )

    def test_validator_rejects_non_reserved_markdown_without_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "index.md").write_text(
                '---\nokf_version: "0.2"\n---\n\n# Bundle\n',
                encoding="utf-8",
            )
            (bundle / "log.md").write_text(
                "# Log\n\n## 2026-01-01\n* **Creation**: Initialized.\n",
                encoding="utf-8",
            )
            (bundle / "bad.md").write_text("# Missing frontmatter\n", encoding="utf-8")

            result = export_okf.validate_okf_bundle(
                bundle,
                now=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )

            self.assertFalse(result["valid"])
            self.assertIn("Missing YAML frontmatter.", [item["message"] for item in result["errors"]])


if __name__ == "__main__":
    unittest.main()
