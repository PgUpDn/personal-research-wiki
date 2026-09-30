#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wiki_pipeline import file_hash
from zotero_import import (
    ImportOptions,
    import_zotero_collection,
    options_from_args,
    pdf_attachments,
    safe_pdf_filename,
    zotero_import_main,
)


PDF_A = b"%PDF-1.4\nfirst attachment\n%%EOF\n"
PDF_B = b"%PDF-1.4\nsecond attachment\n%%EOF\n"
PDF_C = b"%PDF-1.4\nstandalone attachment\n%%EOF\n"


class ZoteroImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.root = base / "repo"
        self.zotero = base / "Zotero Data #1"
        self.root.mkdir()
        self.zotero.mkdir()
        self.database = self.zotero / "zotero.sqlite"
        self._create_database()
        self._write_stored("ATTACH01", "paper.pdf", PDF_A)
        self._write_stored("ATTACH02", "paper.pdf", PDF_B)
        self._write_stored("ATTACH03", "duplicate.pdf", PDF_A)
        self._write_stored("STAND001", "standalone.pdf", PDF_C)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_database(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            create table collections (
                collectionID integer primary key,
                collectionName text,
                parentCollectionID integer,
                libraryID integer,
                key text
            );
            create table deletedCollections (collectionID integer primary key);
            create table collectionItems (collectionID integer, itemID integer);
            create table items (itemID integer primary key, key text);
            create table itemAttachments (
                itemID integer primary key,
                parentItemID integer,
                contentType text,
                path text
            );
            create table deletedItems (itemID integer primary key);

            insert into collections values (10, 'Research', null, 1, 'ROOT0001');
            insert into collections values (11, 'Papers', 10, 1, 'CHILD001');
            insert into collections values (12, 'Deleted child', 10, 1, 'DELETED1');
            insert into collections values (20, 'Research', null, 2, 'ROOT0002');
            insert into deletedCollections values (12);

            insert into items values (100, 'ITEM0001');
            insert into items values (101, 'ATTACH01');
            insert into items values (102, 'ATTACH02');
            insert into items values (103, 'ATTACH03');
            insert into items values (104, 'STAND001');
            insert into items values (105, 'NOFILE01');
            insert into items values (106, 'DELETEDA');
            insert into collectionItems values (11, 100);
            insert into collectionItems values (11, 104);
            insert into collectionItems values (11, 105);
            insert into collectionItems values (11, 106);
            insert into itemAttachments values (101, 100, 'application/pdf', 'storage:paper.pdf');
            insert into itemAttachments values (102, 100, 'application/pdf', 'storage:paper.pdf');
            insert into itemAttachments values (103, 100, 'application/pdf', 'storage:duplicate.pdf');
            insert into itemAttachments values (104, null, 'application/pdf', 'storage:standalone.pdf');
            insert into itemAttachments values (106, 100, 'application/pdf', 'storage:deleted.pdf');
            insert into deletedItems values (106);
            """
        )
        connection.commit()
        connection.close()

    def _write_stored(self, key: str, name: str, content: bytes) -> Path:
        path = self.zotero / "storage" / key / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _options(self, **overrides: object) -> ImportOptions:
        values: dict[str, object] = {
            "root": self.root,
            "database": self.database,
            "zotero_data_dir": self.zotero,
            "collection": "research",
            "library_id": 1,
            "include_subcollections": True,
            "import_base_dir": self.root / "raw/zotero",
            "report_dir": self.root / "_meta/zotero_imports",
        }
        values.update(overrides)
        return ImportOptions(**values)

    def test_dry_run_is_zero_write_and_plans_recursive_unique_imports(self) -> None:
        before_database = file_hash(self.database)
        before_repo = list(self.root.rglob("*"))

        result = import_zotero_collection(self._options(dry_run=True))

        self.assertEqual(before_repo, list(self.root.rglob("*")))
        self.assertEqual(before_database, file_hash(self.database))
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["collection"]["included_collections"], 2)
        self.assertEqual(result["stats"]["items"], 3)
        self.assertEqual(result["stats"]["with_pdf"], 2)
        self.assertEqual(result["stats"]["without_pdf"], 1)
        self.assertEqual(result["stats"]["pdf_attachments"], 4)
        self.assertEqual(result["stats"]["would_import"], 3)
        self.assertEqual(result["stats"]["skipped_duplicate_hash"], 1)
        self.assertEqual(len(set(result["planned"])), 3)
        self.assertIn("raw/zotero/Research/paper.pdf", result["planned"])
        duplicate = next(item for item in result["skipped"] if item["reason"] == "duplicate_hash")
        self.assertEqual(duplicate["duplicate_of"], "raw/zotero/Research/paper.pdf")

    def test_import_is_read_only_idempotent_and_report_is_redacted(self) -> None:
        before_database = file_hash(self.database)
        before_source = file_hash(self.zotero / "storage/ATTACH01/paper.pdf")

        first = import_zotero_collection(self._options())

        self.assertEqual(first["stats"]["imported"], 3)
        self.assertEqual(file_hash(self.database), before_database)
        self.assertEqual(file_hash(self.zotero / "storage/ATTACH01/paper.pdf"), before_source)
        imported = [self.root / path for path in first["imported"]]
        self.assertEqual(sorted(path.read_bytes() for path in imported), sorted([PDF_A, PDF_B, PDF_C]))
        report_path = self.root / first["report"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(self.temporary.name, report_text)
        self.assertNotIn("ATTACH01", report_text)
        self.assertNotIn(file_hash(imported[0]), report_text)

        second = import_zotero_collection(self._options())

        self.assertEqual(second["stats"]["imported"], 0)
        self.assertEqual(second["stats"]["skipped_duplicate_hash"], 4)
        self.assertEqual(len(list((self.root / "raw/zotero/Research").glob("*.pdf"))), 3)

    def test_subcollections_are_opt_in_and_destination_must_be_a_source_dir(self) -> None:
        result = import_zotero_collection(
            self._options(include_subcollections=False, dry_run=True)
        )
        self.assertEqual(result["stats"]["items"], 0)
        self.assertEqual(result["planned"], [])

        with self.assertRaisesRegex(ValueError, "configured source directory"):
            import_zotero_collection(
                self._options(
                    destination=self.root / "output/zotero",
                    dry_run=True,
                )
            )

    def test_ambiguous_collection_requires_library_and_linked_base_is_supported(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
            import_zotero_collection(self._options(library_id=None, dry_run=True))

        linked_base = Path(self.temporary.name) / "linked"
        linked_base.mkdir()
        (linked_base / "linked.pdf").write_bytes(PDF_C + b"linked")
        connection = sqlite3.connect(self.database)
        connection.execute("insert into items values (110, 'LINK0001')")
        connection.execute("insert into items values (111, 'LINKATT1')")
        connection.execute("insert into collectionItems values (11, 110)")
        connection.execute(
            "insert into itemAttachments values (111, 110, 'application/pdf', 'attachments:linked.pdf')"
        )
        connection.commit()
        connection.close()

        without_base = import_zotero_collection(self._options(dry_run=True))
        self.assertEqual(without_base["stats"]["unsafe_paths"], 1)
        with_base = import_zotero_collection(
            self._options(linked_base_dir=linked_base, dry_run=True)
        )
        self.assertEqual(with_base["stats"]["unsafe_paths"], 0)
        self.assertEqual(with_base["stats"]["would_import"], 4)

    def test_cli_lists_collections_and_requires_a_selector_for_import(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = zotero_import_main(
                [
                    "--root",
                    str(self.root),
                    "--database",
                    str(self.database),
                    "--zotero-data-dir",
                    str(self.zotero),
                    "--list-collections",
                ]
            )
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(len(payload["collections"]), 3)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = zotero_import_main(
                [
                    "--root",
                    str(self.root),
                    "--database",
                    str(self.database),
                    "--zotero-data-dir",
                    str(self.zotero),
                    "--dry-run",
                ]
            )
        self.assertEqual(status, 2)
        self.assertIn("Choose exactly one collection", output.getvalue())

    def test_database_option_also_selects_its_attachment_directory(self) -> None:
        import argparse

        args = argparse.Namespace(
            root=str(self.root),
            zotero_data_dir=None,
            database=str(self.database),
            library_id=1,
            collection="Research",
            collection_key=None,
            collection_id=None,
            include_subcollections=True,
            destination=None,
            linked_base_dir=None,
            report_dir=None,
            dry_run=True,
            no_report=False,
            list_collections=False,
        )
        options = options_from_args(args)
        self.assertEqual(options.zotero_data_dir, self.database.parent.resolve())

    def test_large_collection_query_respects_old_sqlite_parameter_limit(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        if hasattr(connection, "setlimit"):
            connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 999)
        attachments = pdf_attachments(connection, list(range(1, 502)))
        self.assertEqual(len(attachments), 4)
        connection.close()

    def test_wal_database_snapshot_does_not_touch_zotero_sidecars(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute("pragma journal_mode = wal")
        connection.execute("insert into collections values (30, 'WAL only', null, 1, 'WAL00001')")
        connection.commit()
        connection.execute("pragma wal_checkpoint(passive)")

        def snapshot() -> dict[str, tuple[int, int, str]]:
            result = {}
            for path in sorted(self.zotero.iterdir()):
                if path.is_file():
                    metadata = path.stat()
                    result[path.name] = (metadata.st_size, metadata.st_mtime_ns, file_hash(path))
            return result

        before = snapshot()
        result = import_zotero_collection(
            self._options(collection="WAL only", include_subcollections=False, dry_run=True)
        )
        after = snapshot()
        connection.close()

        self.assertEqual(result["collection"]["name"], "WAL only")
        self.assertEqual(before, after)

    def test_active_rollback_journal_is_rejected_without_touching_zotero(self) -> None:
        writer_script = """
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
connection.execute("pragma journal_mode = delete")
connection.execute("pragma cache_size = 1")
connection.execute("begin immediate")
for index in range(50):
    connection.execute(
        "insert into collections values (?, ?, null, 1, ?)",
        (1000 + index, "Uncommitted", f"TX{index:06d}"),
    )
print("ready", flush=True)
sys.stdin.readline()
connection.rollback()
connection.close()
"""
        writer = subprocess.Popen(
            [sys.executable, "-c", writer_script, str(self.database)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        self.assertIsNotNone(writer.stdout)
        self.assertEqual(writer.stdout.readline().strip(), "ready")

        try:
            journal = Path(f"{self.database}-journal")
            self.assertTrue(journal.is_file())
            self.assertGreater(journal.stat().st_size, 0)

            def snapshot() -> dict[str, tuple[int, int, str]]:
                result = {}
                for path in sorted(self.zotero.iterdir()):
                    if path.is_file():
                        metadata = path.stat()
                        result[path.name] = (metadata.st_size, metadata.st_mtime_ns, file_hash(path))
                return result

            before = snapshot()
            with self.assertRaisesRegex(RuntimeError, "Close Zotero and retry"):
                import_zotero_collection(self._options(dry_run=True))
            after = snapshot()

            self.assertEqual(before, after)
        finally:
            self.assertIsNotNone(writer.stdin)
            writer.stdin.write("\n")
            writer.stdin.flush()
            writer.communicate(timeout=5)

    def test_inactive_zeroed_rollback_journal_is_ignored(self) -> None:
        journal = Path(f"{self.database}-journal")
        journal.write_bytes(b"\0" * 4096)
        before = file_hash(journal)

        result = import_zotero_collection(self._options(dry_run=True))

        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["stats"]["would_import"], 3)
        self.assertEqual(file_hash(journal), before)

    def test_binary_different_pdfs_with_identical_content_are_deduplicated(self) -> None:
        first = self.zotero / "storage/VISUAL01/duplicate.pdf"
        second = self.zotero / "storage/VISUAL02/duplicate.pdf"
        for path, producer in ((first, "first"), (second, "second")):
            path.parent.mkdir(parents=True)
            document = pymupdf.open()
            page = document.new_page()
            page.insert_text((72, 72), "Same paper content")
            document.set_metadata({"producer": producer})
            document.save(path)
            document.close()

        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            insert into items values (120, 'VISUAL01');
            insert into items values (121, 'VISUAL02');
            insert into collectionItems values (11, 120);
            insert into collectionItems values (11, 121);
            insert into itemAttachments values (120, null, 'application/pdf', 'storage:duplicate.pdf');
            insert into itemAttachments values (121, null, 'application/pdf', 'storage:duplicate.pdf');
            """
        )
        connection.commit()
        connection.close()

        result = import_zotero_collection(self._options(dry_run=True))

        self.assertEqual(result["stats"]["skipped_duplicate_content"], 1)
        self.assertEqual(result["stats"]["would_import"], 4)
        duplicate = next(
            item for item in result["skipped"] if item["reason"] == "duplicate_content"
        )
        self.assertTrue(duplicate["duplicate_of"].startswith("raw/zotero/Research/"))

    def test_existing_clipping_title_prevents_duplicate_pdf_import(self) -> None:
        clipping_dir = self.root / "Clippings"
        clipping_dir.mkdir()
        clipping = clipping_dir / "A Distinctive Existing Research Paper.md"
        clipping.write_text("# A Distinctive Existing Research Paper\n", encoding="utf-8")
        self._write_stored("TITLE001", "Author - 2026 - A Distinctive Existing Research Paper.pdf", PDF_C + b"title")

        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            insert into items values (130, 'TITLEPAR');
            insert into items values (131, 'TITLE001');
            insert into collectionItems values (11, 130);
            insert into itemAttachments values (
                131,
                130,
                'application/pdf',
                'storage:Author - 2026 - A Distinctive Existing Research Paper.pdf'
            );
            """
        )
        connection.commit()
        connection.close()

        result = import_zotero_collection(self._options(dry_run=True))

        self.assertEqual(result["stats"]["skipped_duplicate_title"], 1)
        duplicate = next(
            item for item in result["skipped"] if item["reason"] == "duplicate_title"
        )
        self.assertEqual(duplicate["duplicate_of"], "Clippings/A Distinctive Existing Research Paper.md")

    def test_filenames_fit_common_limits_and_avoid_windows_device_names(self) -> None:
        self.assertLessEqual(len(safe_pdf_filename("研究" * 120).encode("utf-8")), 255)
        self.assertEqual(safe_pdf_filename("CON.pdf"), "_CON.pdf")


if __name__ == "__main__":
    unittest.main()
