#!/usr/bin/env python3

"""Import PDF attachments from a local Zotero collection.

The Zotero database is opened read-only.  Importing means copying attachments
into one of the wiki's configured source directories; Zotero itself is never
modified.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from wiki_pipeline import configured_source_dirs, file_hash, load_config, parse_root_arg


@dataclass(frozen=True)
class ImportOptions:
    root: Path
    database: Path
    zotero_data_dir: Path
    collection: str | None = None
    collection_key: str | None = None
    collection_id: int | None = None
    library_id: int | None = None
    include_subcollections: bool = False
    destination: Path | None = None
    import_base_dir: Path | None = None
    linked_base_dir: Path | None = None
    report_dir: Path | None = None
    write_report: bool = True
    dry_run: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "root",
            "database",
            "zotero_data_dir",
            "destination",
            "import_base_dir",
            "linked_base_dir",
            "report_dir",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, Path(value).expanduser().resolve())


@dataclass(frozen=True)
class PlannedCopy:
    source: Path
    destination: Path
    digest: str
    attachment_kind: str


REQUIRED_SCHEMA = {
    "collections": {
        "collectionID",
        "collectionName",
        "parentCollectionID",
        "libraryID",
        "key",
    },
    "collectionItems": {"collectionID", "itemID"},
    "items": {"itemID", "key"},
    "itemAttachments": {"itemID", "parentItemID", "contentType", "path"},
    "deletedItems": {"itemID"},
    "deletedCollections": {"collectionID"},
}


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_repo_path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def resolve_external_path(value: str | Path, *, relative_to: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and relative_to is not None:
        path = relative_to / path
    return path.resolve()


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f'pragma table_info("{table}")')}


def validate_schema(connection: sqlite3.Connection) -> None:
    problems = []
    for table, required_columns in REQUIRED_SCHEMA.items():
        columns = table_columns(connection, table)
        if not columns:
            problems.append(f"missing table {table}")
            continue
        missing = sorted(required_columns - columns)
        if missing:
            problems.append(f"{table} missing columns: {', '.join(missing)}")
    if problems:
        raise RuntimeError(
            "Unsupported Zotero SQLite schema ("
            + "; ".join(problems)
            + "). Update the connector before using this Zotero version."
        )


def database_snapshot_signature(database: Path) -> tuple[tuple[str, int, int, int, int], ...]:
    signature = []
    for suffix in ("", "-wal", "-journal"):
        path = Path(f"{database}{suffix}")
        if path.exists():
            metadata = path.stat()
            signature.append(
                (suffix, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
            )
    return tuple(signature)


def rollback_journal_is_active(database: Path) -> bool:
    journal = Path(f"{database}-journal")
    try:
        if not journal.is_file() or journal.stat().st_size == 0:
            return False
        with journal.open("rb") as handle:
            has_live_header = any(handle.read(8))
        with database.open("rb") as handle:
            try:
                fcntl.lockf(
                    handle.fileno(),
                    fcntl.LOCK_SH | fcntl.LOCK_NB,
                    1,
                    0x40000001,
                    os.SEEK_SET,
                )
            except BlockingIOError:
                has_reserved_lock = True
            else:
                has_reserved_lock = False
                fcntl.lockf(
                    handle.fileno(),
                    fcntl.LOCK_UN,
                    1,
                    0x40000001,
                    os.SEEK_SET,
                )
        return has_live_header or has_reserved_lock
    except OSError:
        return True


def copy_database_snapshot(database: Path, attempts: int = 3) -> tempfile.TemporaryDirectory[str]:
    if not database.is_file():
        raise FileNotFoundError(f"Zotero database not found: {database}")
    last_error = "source changed while it was copied"
    for attempt in range(attempts):
        if rollback_journal_is_active(database):
            last_error = "an active SQLite rollback journal is present"
            if attempt + 1 < attempts:
                time.sleep(0.05)
                continue
            break
        before = database_snapshot_signature(database)
        temporary = tempfile.TemporaryDirectory(prefix="research-wiki-zotero-")
        snapshot_dir = Path(temporary.name)
        snapshot_database = snapshot_dir / "zotero.sqlite"
        try:
            shutil.copyfile(database, snapshot_database)
            source_wal = Path(f"{database}-wal")
            if source_wal.is_file():
                shutil.copyfile(source_wal, snapshot_dir / "zotero.sqlite-wal")
            after = database_snapshot_signature(database)
            if before != after or rollback_journal_is_active(database):
                last_error = "source changed while it was copied"
                temporary.cleanup()
                if attempt + 1 < attempts:
                    time.sleep(0.05)
                continue
            for path in snapshot_dir.iterdir():
                path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            check = sqlite3.connect(snapshot_database)
            try:
                quick_check = check.execute("pragma quick_check").fetchone()
                if not quick_check or quick_check[0] != "ok":
                    last_error = "snapshot failed SQLite quick_check"
                    check.close()
                    temporary.cleanup()
                    if attempt + 1 < attempts:
                        time.sleep(0.05)
                    continue
            finally:
                with contextlib.suppress(sqlite3.Error):
                    check.close()
            return temporary
        except (OSError, sqlite3.Error) as error:
            last_error = str(error)
            temporary.cleanup()
            if attempt + 1 < attempts:
                time.sleep(0.05)
    raise RuntimeError(
        "Could not take a consistent read-only snapshot of the Zotero database "
        f"({last_error}). Close Zotero and retry."
    )


def open_read_only_database(database: Path) -> sqlite3.Connection:
    if not database.is_file():
        raise FileNotFoundError(f"Zotero database not found: {database}")
    connection = sqlite3.connect(
        f"{database.resolve().as_uri()}?mode=ro",
        uri=True,
        timeout=10,
    )
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("pragma query_only = on")
        validate_schema(connection)
        return connection
    except Exception:
        connection.close()
        raise


def open_zotero_snapshot(
    database: Path,
) -> tuple[tempfile.TemporaryDirectory[str], sqlite3.Connection]:
    temporary = copy_database_snapshot(database)
    snapshot_database = Path(temporary.name) / "zotero.sqlite"
    try:
        return temporary, open_read_only_database(snapshot_database)
    except Exception:
        temporary.cleanup()
        raise


def available_collections(
    connection: sqlite3.Connection,
    library_id: int | None = None,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        select c.collectionID, c.collectionName, c.parentCollectionID,
               c.libraryID, c.key
        from collections c
        where not exists (
            select 1 from deletedCollections dc where dc.collectionID = c.collectionID
        )
        order by lower(c.collectionName), c.collectionID
        """
    ).fetchall()
    collections = [
        {
            "collection_id": int(row["collectionID"]),
            "name": str(row["collectionName"] or ""),
            "parent_id": (
                int(row["parentCollectionID"])
                if row["parentCollectionID"] is not None
                else None
            ),
            "library_id": int(row["libraryID"]),
            "collection_key": str(row["key"] or ""),
        }
        for row in rows
    ]
    if library_id is not None:
        collections = [item for item in collections if item["library_id"] == library_id]
    return collections


def select_collection(
    collections: list[dict[str, Any]],
    *,
    name: str | None,
    key: str | None,
    collection_id: int | None,
) -> dict[str, Any]:
    selectors = [name is not None, key is not None, collection_id is not None]
    if sum(selectors) != 1:
        raise ValueError(
            "Choose exactly one collection with --collection, --collection-key, "
            "or --collection-id."
        )
    if name is not None:
        matches = [item for item in collections if item["name"].casefold() == name.casefold()]
    elif key is not None:
        matches = [item for item in collections if item["collection_key"] == key]
    else:
        matches = [item for item in collections if item["collection_id"] == collection_id]
    if not matches:
        raise RuntimeError("The requested Zotero collection was not found.")
    if len(matches) > 1:
        candidates = ", ".join(
            f"library={item['library_id']} key={item['collection_key']}"
            for item in matches
        )
        raise RuntimeError(
            "The requested collection is ambiguous. Add --library-id or use "
            f"--collection-id. Matches: {candidates}"
        )
    return matches[0]


def selected_collection_ids(
    collections: list[dict[str, Any]],
    selected: dict[str, Any],
    include_subcollections: bool,
) -> list[int]:
    selected_ids = [int(selected["collection_id"])]
    if not include_subcollections:
        return selected_ids
    children: dict[int, list[int]] = {}
    for item in collections:
        parent_id = item["parent_id"]
        if parent_id is not None:
            children.setdefault(int(parent_id), []).append(int(item["collection_id"]))
    cursor = 0
    seen = set(selected_ids)
    while cursor < len(selected_ids):
        parent_id = selected_ids[cursor]
        cursor += 1
        for child_id in children.get(parent_id, []):
            if child_id not in seen:
                seen.add(child_id)
                selected_ids.append(child_id)
    return selected_ids


def collection_item_ids(
    connection: sqlite3.Connection,
    collection_ids: list[int],
) -> list[int]:
    item_ids = set()
    for start in range(0, len(collection_ids), 400):
        chunk = collection_ids[start : start + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows = connection.execute(
            f"""
            select distinct ci.itemID
            from collectionItems ci
            where ci.collectionID in ({placeholders})
              and not exists (
                select 1 from deletedItems di where di.itemID = ci.itemID
              )
            """,
            chunk,
        ).fetchall()
        item_ids.update(int(row[0]) for row in rows)
    return sorted(item_ids)


def pdf_attachments(
    connection: sqlite3.Connection,
    item_ids: list[int],
) -> list[dict[str, Any]]:
    if not item_ids:
        return []
    rows = []
    for start in range(0, len(item_ids), 400):
        chunk = item_ids[start : start + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows.extend(
            connection.execute(
                f"""
                select ia.itemID as attachmentItemID, ia.parentItemID,
                       ia.contentType, ia.path, ai.key as attachmentKey
                from itemAttachments ia
                join items ai on ai.itemID = ia.itemID
                where (
                    ia.parentItemID in ({placeholders})
                    or (
                        (ia.parentItemID is null or ia.parentItemID = 0)
                        and ia.itemID in ({placeholders})
                    )
                )
                  and not exists (
                    select 1 from deletedItems di where di.itemID = ia.itemID
                  )
                  and (
                    ia.parentItemID is null
                    or ia.parentItemID = 0
                    or not exists (
                        select 1 from deletedItems dp where dp.itemID = ia.parentItemID
                    )
                  )
                """,
                [*chunk, *chunk],
            ).fetchall()
        )
    rows.sort(
        key=lambda row: (
            int(row["parentItemID"] or row["attachmentItemID"]),
            int(row["attachmentItemID"]),
        )
    )
    attachments = []
    for row in rows:
        raw_path = row["path"]
        content_type = str(row["contentType"] or "").casefold()
        looks_like_pdf = "pdf" in content_type or str(raw_path or "").casefold().endswith(".pdf")
        if not looks_like_pdf:
            continue
        parent_id = row["parentItemID"]
        attachments.append(
            {
                "attachment_id": int(row["attachmentItemID"]),
                "logical_item_id": (
                    int(parent_id) if parent_id not in (None, 0) else int(row["attachmentItemID"])
                ),
                "attachment_key": str(row["attachmentKey"] or ""),
                "path": str(raw_path) if raw_path is not None else None,
            }
        )
    return attachments


def read_collection(
    options: ImportOptions,
) -> tuple[dict[str, Any], list[int], list[int], list[dict[str, Any]]]:
    snapshot, connection = open_zotero_snapshot(options.database)
    try:
        connection.execute("begin")
        collections = available_collections(connection, options.library_id)
        selected = select_collection(
            collections,
            name=options.collection,
            key=options.collection_key,
            collection_id=options.collection_id,
        )
        collection_ids = selected_collection_ids(
            collections,
            selected,
            options.include_subcollections,
        )
        item_ids = collection_item_ids(connection, collection_ids)
        attachments = pdf_attachments(connection, item_ids)
        connection.rollback()
        return selected, collection_ids, item_ids, attachments
    finally:
        connection.close()
        snapshot.cleanup()


def safe_component(value: str, fallback: str) -> str:
    name = unicodedata.normalize("NFKC", value or fallback)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    name = name or fallback
    encoded = name.encode("utf-8")
    if len(encoded) > 180:
        encoded = encoded[:180]
        while True:
            try:
                name = encoded.decode("utf-8")
                break
            except UnicodeDecodeError:
                encoded = encoded[:-1]
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"COM{index}" for index in range(1, 10))
    reserved.update(f"LPT{index}" for index in range(1, 10))
    if Path(name).stem.upper() in reserved:
        name = f"_{name}"
    return name.strip(" .") or fallback


def safe_pdf_filename(value: str) -> str:
    name = safe_component(value, "zotero-source.pdf")
    if not name.casefold().endswith(".pdf"):
        name += ".pdf"
    stem = Path(name).stem[:180].strip(" .") or "zotero-source"
    return f"{stem}.pdf"


def safe_join(base: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("absolute path in relative Zotero attachment")
    candidate = (base / relative_path).resolve()
    if not path_is_within(candidate, base.resolve()):
        raise ValueError("Zotero attachment path leaves its configured base directory")
    return candidate


def resolve_attachment_path(
    zotero_data_dir: Path,
    attachment_key: str,
    attachment_path: str | None,
    linked_base_dir: Path | None,
) -> tuple[Path, str]:
    if not attachment_path:
        raise ValueError("attachment has no local path")
    if attachment_path.startswith("storage:"):
        if not attachment_key or Path(attachment_key).name != attachment_key:
            raise ValueError("invalid Zotero storage key")
        relative = attachment_path.split(":", 1)[1]
        return safe_join(zotero_data_dir / "storage" / attachment_key, relative), "stored"
    if attachment_path.startswith("attachments:"):
        if linked_base_dir is None:
            raise ValueError("linked attachment requires --linked-base-dir")
        relative = attachment_path.split(":", 1)[1]
        return safe_join(linked_base_dir, relative), "linked-base"
    path = Path(attachment_path).expanduser()
    if path.is_absolute():
        return path.resolve(), "linked-absolute"
    return safe_join(zotero_data_dir, attachment_path), "linked-relative"


def existing_pdf_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.suffix.casefold() != ".pdf":
                continue
            try:
                hashes.setdefault(file_hash(path), path.relative_to(root).as_posix())
            except OSError:
                continue
    return hashes


def source_title_key(name: str) -> str | None:
    stem = unicodedata.normalize("NFKC", Path(name).stem)
    parts = [part.strip() for part in stem.split(" - ") if part.strip()]
    if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]):
        stem = " - ".join(parts[2:])
    elif len(parts) >= 2:
        stem = " - ".join(parts[1:])
    stem = re.sub(r"-[0-9a-f]{8}$", "", stem, flags=re.IGNORECASE)
    normalized = re.sub(r"[^a-z0-9]+", " ", stem.casefold()).strip()
    meaningful_tokens = [token for token in normalized.split() if len(token) >= 3]
    if len(meaningful_tokens) < 3 or len(normalized) < 24:
        return None
    return normalized


def existing_source_titles(root: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.suffix.casefold() not in {".pdf", ".md"}:
                continue
            title_key = source_title_key(path.name)
            if title_key:
                titles.setdefault(title_key, path.relative_to(root).as_posix())
    return titles


def pdf_content_fingerprint(path: Path) -> str | None:
    try:
        with pymupdf.open(path) as document:
            text = " ".join(
                unicodedata.normalize("NFKC", page.get_text("text")).casefold()
                for page in document
            )
            normalized_text = re.sub(r"\s+", " ", text).strip()
            if normalized_text:
                digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
                return f"text-v1:{digest}"

            digest = hashlib.sha256()
            digest.update(f"pages:{document.page_count}\n".encode("ascii"))
            for page in document:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(0.5, 0.5),
                    colorspace=pymupdf.csGRAY,
                    alpha=False,
                )
                digest.update(f"{pixmap.width}x{pixmap.height}:".encode("ascii"))
                digest.update(pixmap.samples)
            return f"visual-v1:{digest.hexdigest()}"
    except (OSError, RuntimeError, ValueError):
        return None


def unique_destination(
    destination_dir: Path,
    source_name: str,
    digest: str,
    reserved: set[str],
) -> Path:
    base_name = safe_pdf_filename(source_name)
    candidate = destination_dir / base_name
    if candidate.name.casefold() not in reserved and not candidate.exists():
        reserved.add(candidate.name.casefold())
        return candidate
    stem = Path(base_name).stem[:165].strip(" .") or "zotero-source"
    candidate = destination_dir / f"{stem}-{digest[:8]}.pdf"
    index = 2
    while candidate.name.casefold() in reserved or candidate.exists():
        candidate = destination_dir / f"{stem[:155]}-{digest[:8]}-{index}.pdf"
        index += 1
    reserved.add(candidate.name.casefold())
    return candidate


def validate_destination(root: Path, destination: Path) -> None:
    if not path_is_within(destination, root):
        raise ValueError("Zotero destination must remain inside the repository.")
    source_dirs = [path.resolve() for path in configured_source_dirs(root)]
    if not any(path_is_within(destination, source_dir) for source_dir in source_dirs):
        configured = ", ".join(path.relative_to(root).as_posix() for path in source_dirs)
        raise ValueError(
            "Zotero destination must be inside a configured source directory "
            f"({configured})."
        )


def import_destination(options: ImportOptions, selected: dict[str, Any]) -> Path:
    if options.destination is not None:
        destination = options.destination.resolve()
    else:
        if options.import_base_dir is None:
            raise ValueError("No Zotero import directory is configured.")
        folder = safe_component(str(selected["name"]), "zotero-collection")
        destination = (options.import_base_dir / folder).resolve()
    validate_destination(options.root, destination)
    return destination


def build_import_plan(
    options: ImportOptions,
    destination_dir: Path,
    item_ids: list[int],
    attachments: list[dict[str, Any]],
) -> tuple[list[PlannedCopy], dict[str, int], list[dict[str, str]]]:
    existing_hashes = existing_pdf_hashes(options.root)
    seen_hashes = dict(existing_hashes)
    seen_titles = existing_source_titles(options.root)
    reserved = (
        {path.name.casefold() for path in destination_dir.iterdir() if path.is_file()}
        if destination_dir.exists()
        else set()
    )
    stats = {
        "items": len(item_ids),
        "with_pdf": 0,
        "without_pdf": 0,
        "pdf_attachments": len(attachments),
        "would_import": 0,
        "imported": 0,
        "skipped_duplicate_hash": 0,
        "skipped_duplicate_title": 0,
        "skipped_duplicate_content": 0,
        "missing_files": 0,
        "unsafe_paths": 0,
        "copy_failures": 0,
    }
    item_id_set = set(item_ids)
    with_pdf = {item["logical_item_id"] for item in attachments} & item_id_set
    stats["with_pdf"] = len(with_pdf)
    stats["without_pdf"] = len(item_id_set - with_pdf)
    planned = []
    skipped = []
    seen_content_fingerprints: dict[str, str] = {}
    for attachment in attachments:
        try:
            source, attachment_kind = resolve_attachment_path(
                options.zotero_data_dir,
                str(attachment["attachment_key"]),
                attachment["path"],
                options.linked_base_dir,
            )
        except ValueError as error:
            stats["unsafe_paths"] += 1
            skipped.append({"reason": "unresolved_or_unsafe_path", "detail": str(error)})
            continue
        if not source.is_file():
            stats["missing_files"] += 1
            skipped.append(
                {
                    "reason": "missing_file",
                    "attachment": safe_pdf_filename(source.name),
                    "attachment_kind": attachment_kind,
                }
            )
            continue
        try:
            digest = file_hash(source)
        except OSError as error:
            stats["missing_files"] += 1
            skipped.append({"reason": "unreadable_file", "detail": str(error)})
            continue
        duplicate_of = seen_hashes.get(digest)
        if duplicate_of is not None:
            stats["skipped_duplicate_hash"] += 1
            skipped.append(
                {
                    "reason": "duplicate_hash",
                    "attachment": safe_pdf_filename(source.name),
                    "duplicate_of": duplicate_of,
                }
            )
            continue
        title_key = source_title_key(source.name)
        duplicate_title_of = seen_titles.get(title_key) if title_key else None
        if duplicate_title_of is not None:
            stats["skipped_duplicate_title"] += 1
            skipped.append(
                {
                    "reason": "duplicate_title",
                    "attachment": safe_pdf_filename(source.name),
                    "duplicate_of": duplicate_title_of,
                }
            )
            continue
        content_fingerprint = pdf_content_fingerprint(source)
        duplicate_content_of = (
            seen_content_fingerprints.get(content_fingerprint)
            if content_fingerprint is not None
            else None
        )
        if duplicate_content_of is not None:
            stats["skipped_duplicate_content"] += 1
            skipped.append(
                {
                    "reason": "duplicate_content",
                    "attachment": safe_pdf_filename(source.name),
                    "duplicate_of": duplicate_content_of,
                }
            )
            continue
        destination = unique_destination(destination_dir, source.name, digest, reserved)
        relative_destination = destination.relative_to(options.root).as_posix()
        seen_hashes[digest] = relative_destination
        if title_key:
            seen_titles[title_key] = relative_destination
        if content_fingerprint is not None:
            seen_content_fingerprints[content_fingerprint] = relative_destination
        planned.append(PlannedCopy(source, destination, digest, attachment_kind))
    stats["would_import"] = len(planned)
    return planned, stats, skipped


def atomic_copy(planned: PlannedCopy) -> None:
    planned.destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{planned.destination.name}.",
        suffix=".tmp",
        dir=planned.destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(planned.source, temporary)
        if file_hash(temporary) != planned.digest:
            raise OSError("copied attachment failed SHA-256 verification")
        try:
            os.link(temporary, planned.destination)
        except FileExistsError as error:
            raise OSError(f"destination appeared during import: {planned.destination.name}") from error
    finally:
        temporary.unlink(missing_ok=True)


def write_summary_report(
    options: ImportOptions,
    destination_dir: Path,
    stats: dict[str, int],
) -> Path | None:
    if options.dry_run or not options.write_report or options.report_dir is None:
        return None
    report_dir = options.report_dir.resolve()
    if not path_is_within(report_dir, options.root):
        raise ValueError("Zotero report directory must remain inside the repository.")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = report_dir / f"{timestamp}-zotero-import-summary.json"
    report = {
        "schema_version": "zotero-import-summary-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "privacy": "summary-only; no Zotero paths, item metadata, keys, or hashes",
        "destination_dir": destination_dir.relative_to(options.root).as_posix(),
        "stats": stats,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def validate_report_destination(options: ImportOptions) -> None:
    if options.dry_run or not options.write_report or options.report_dir is None:
        return
    if not path_is_within(options.report_dir.resolve(), options.root):
        raise ValueError("Zotero report directory must remain inside the repository.")


def import_zotero_collection(options: ImportOptions) -> dict[str, Any]:
    selected, collection_ids, item_ids, attachments = read_collection(options)
    destination_dir = import_destination(options, selected)
    validate_report_destination(options)
    planned, stats, skipped = build_import_plan(
        options,
        destination_dir,
        item_ids,
        attachments,
    )
    imported = []
    if not options.dry_run:
        for copy in planned:
            try:
                atomic_copy(copy)
            except OSError as error:
                stats["copy_failures"] += 1
                skipped.append(
                    {
                        "reason": "copy_failed",
                        "attachment": safe_pdf_filename(copy.source.name),
                        "detail": str(error),
                    }
                )
                continue
            stats["imported"] += 1
            imported.append(copy.destination.relative_to(options.root).as_posix())
    report_path = write_summary_report(options, destination_dir, stats)
    result: dict[str, Any] = {
        "status": "dry-run" if options.dry_run else "completed",
        "collection": {
            "name": selected["name"],
            "library_id": selected["library_id"],
            "included_collections": len(collection_ids),
        },
        "database": options.database.name,
        "destination_dir": destination_dir.relative_to(options.root).as_posix(),
        "stats": stats,
        "skipped": skipped,
    }
    if options.dry_run:
        result["planned"] = [
            copy.destination.relative_to(options.root).as_posix() for copy in planned
        ]
        result["report"] = None
    else:
        result["imported"] = imported
        result["report"] = (
            report_path.relative_to(options.root).as_posix() if report_path is not None else None
        )
    return result


def add_zotero_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=None)
    parser.add_argument("--zotero-data-dir", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--library-id", type=int, default=None)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--collection", default=None)
    selector.add_argument("--collection-key", default=None)
    selector.add_argument("--collection-id", type=int, default=None)
    parser.add_argument("--include-subcollections", action="store_true")
    parser.add_argument("--destination", default=None)
    parser.add_argument("--linked-base-dir", default=None)
    parser.add_argument("--report-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--list-collections", action="store_true")


def options_from_args(args: argparse.Namespace) -> ImportOptions:
    root = parse_root_arg(args.root)
    config = load_config(root)
    configured_zotero_dir = config.get("zotero_data_dir", "~/Zotero")
    zotero_value = args.zotero_data_dir or configured_zotero_dir
    if args.database and not args.zotero_data_dir:
        zotero_value = Path(args.database).expanduser().resolve().parent
    zotero_data_dir = resolve_external_path(
        zotero_value,
        relative_to=root if args.zotero_data_dir is None else None,
    )
    database = (
        resolve_external_path(args.database)
        if args.database
        else (zotero_data_dir / "zotero.sqlite").resolve()
    )
    configured_linked_base = config.get("zotero_linked_attachment_base_dir")
    linked_base_dir = None
    if args.linked_base_dir:
        linked_base_dir = resolve_external_path(args.linked_base_dir)
    elif configured_linked_base:
        linked_base_dir = resolve_external_path(configured_linked_base, relative_to=root)
    destination = resolve_repo_path(root, args.destination) if args.destination else None
    import_base_dir = resolve_repo_path(
        root,
        config.get("zotero_import_dir", "raw/zotero"),
    )
    report_dir = resolve_repo_path(
        root,
        args.report_dir or config.get("zotero_report_dir", "_meta/zotero_imports"),
    )
    return ImportOptions(
        root=root,
        database=database,
        zotero_data_dir=zotero_data_dir,
        collection=args.collection,
        collection_key=args.collection_key,
        collection_id=args.collection_id,
        library_id=args.library_id,
        include_subcollections=args.include_subcollections,
        destination=destination,
        import_base_dir=import_base_dir,
        linked_base_dir=linked_base_dir,
        report_dir=report_dir,
        write_report=not args.no_report,
        dry_run=args.dry_run,
    )


def run_zotero_args(args: argparse.Namespace) -> int:
    try:
        options = options_from_args(args)
        if args.list_collections:
            snapshot, connection = open_zotero_snapshot(options.database)
            try:
                collections = available_collections(connection, options.library_id)
            finally:
                connection.close()
                snapshot.cleanup()
            print(json.dumps({"collections": collections}, ensure_ascii=False, indent=2))
            return 0
        result = import_zotero_collection(options)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        failures = (
            result["stats"]["missing_files"]
            + result["stats"]["unsafe_paths"]
            + result["stats"]["copy_failures"]
        )
        return 1 if failures else 0
    except (FileNotFoundError, OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 2


def zotero_import_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy PDF attachments from a Zotero collection into the research wiki."
    )
    add_zotero_arguments(parser)
    return run_zotero_args(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(zotero_import_main())
