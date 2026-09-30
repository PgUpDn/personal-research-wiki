#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import zipfile
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

from wiki_pipeline import detect_title, load_config, note_blurb, parse_root_arg, read_text, slugify, strip_frontmatter


OKF_VERSION = "0.2"
PRODUCER = "process:research-wiki-compiler"
RESERVED_FILENAMES = {"index.md", "log.md"}
COLLECTIONS = ("projects", "concepts", "sources", "derived", "system")
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?P<label>!?\[[^\]]*\])\((?P<target><[^>]+>|[^)\n]+)\)")
LOG_ENTRY_RE = re.compile(r"^## \[(?P<timestamp>[^\]]+)\]\s+(?P<category>[^|]+)\|\s*(?P<title>.+)$")


def utc_timestamp(value: float | None = None) -> str:
    current = datetime.fromtimestamp(value, timezone.utc) if value is not None else datetime.now(timezone.utc)
    return current.isoformat(timespec="seconds").replace("+00:00", "Z")


def file_timestamp(path: Path) -> str:
    return utc_timestamp(path.stat().st_mtime)


def compact_text(value: str, limit: int = 240) -> str:
    value = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[`*_>#]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -")
    if len(value) <= limit:
        return value
    shortened = value[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}…"


def frontmatter_text(markdown_text: str) -> str:
    if not markdown_text.startswith("---\n"):
        return ""
    end = markdown_text.find("\n---", 4)
    if end < 0:
        return ""
    return markdown_text[4:end]


def scalar_field(markdown_text: str, key: str) -> str | None:
    frontmatter = frontmatter_text(markdown_text)
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw or raw in {"[]", "{}", "null", "~"}:
        return None
    if raw.startswith(('"', "'")) and raw.endswith(raw[0]):
        return raw[1:-1]
    return raw


def list_field(markdown_text: str, key: str) -> list[str]:
    frontmatter = frontmatter_text(markdown_text)
    inline = re.search(rf"^{re.escape(key)}:\s*(\[[^\n]*\])\s*$", frontmatter, re.MULTILINE)
    if inline:
        try:
            values = json.loads(inline.group(1))
        except json.JSONDecodeError:
            values = []
        return [str(value).strip() for value in values if str(value).strip()]
    block = re.search(rf"^{re.escape(key)}:\s*\n((?:  - .*\n?)*)", frontmatter, re.MULTILINE)
    if not block:
        return []
    values = []
    for line in block.group(1).splitlines():
        item = line.strip()
        if not item.startswith("- "):
            continue
        value = item[2:].strip()
        if value.startswith(('"', "'")) and value.endswith(value[0]):
            value = value[1:-1]
        if value:
            values.append(value)
    return values


def section_excerpt(markdown_text: str, headings: tuple[str, ...]) -> str | None:
    body = strip_frontmatter(markdown_text)
    lines = body.splitlines()
    normalized = {heading.lower() for heading in headings}
    for index, line in enumerate(lines):
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line.strip())
        if not match or match.group(1).strip().lower() not in normalized:
            continue
        collected = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if stripped.startswith("#"):
                break
            if not stripped or stripped.startswith((">", "- ", "* ", "|", "```")):
                if collected:
                    break
                continue
            collected.append(stripped)
            if len(" ".join(collected)) > 360:
                break
        if collected:
            return compact_text(" ".join(collected))
    return None


def description_for(markdown_text: str, note_type: str) -> str:
    headings_by_type = {
        "source": ("TL;DR", "Abstract"),
        "concept": ("Definition",),
        "project": ("Programme Thesis", "Project Thesis"),
        "derived": ("Answer",),
        "system": ("Purpose", "Design Goals", "Main Pipeline"),
    }
    excerpt = section_excerpt(markdown_text, headings_by_type.get(note_type, ()))
    if excerpt:
        return excerpt
    return compact_text(note_blurb(markdown_text)) or "Research wiki knowledge document."


def collect_native_documents(root: Path) -> list[Path]:
    config = load_config(root)
    wiki_dir = root / config["wiki_dir"]
    paths = [
        path
        for path in sorted(wiki_dir.glob("*.md"))
        if path.name not in {"INDEX.md", "LOG.md"}
    ]
    for key, default in (
        ("projects_dir", "wiki/projects"),
        ("concepts_dir", "wiki/concepts"),
        ("source_notes_dir", "wiki/sources"),
        ("derived_wiki_dir", "wiki/derived"),
    ):
        paths.extend(
            path
            for path in sorted((root / config.get(key, default)).glob("*.md"))
            if path.name.lower() != "readme.md"
        )
    schema_path = root / config.get("schema_path", "AGENTS.md")
    if schema_path.exists():
        paths.append(schema_path)
    return list(dict.fromkeys(path.resolve() for path in paths if path.is_file()))


def destination_for(root: Path, source_path: Path) -> Path:
    relative = source_path.relative_to(root)
    if relative == Path("AGENTS.md"):
        return Path("system/schema.md")
    if relative.parts[:2] == ("wiki", "projects"):
        return Path("projects") / relative.name
    if relative.parts[:2] == ("wiki", "concepts"):
        return Path("concepts") / relative.name
    if relative.parts[:2] == ("wiki", "sources"):
        return Path("sources") / relative.name
    if relative.parts[:2] == ("wiki", "derived"):
        return Path("derived") / relative.name
    if relative.parts and relative.parts[0] == "wiki":
        return Path("system") / f"{slugify(relative.stem) or relative.stem.lower()}.md"
    return Path("system") / f"{slugify(relative.stem) or relative.stem.lower()}.md"


def note_type_for(path: Path, markdown_text: str, root: Path) -> str:
    declared = (scalar_field(markdown_text, "note_type") or "").lower()
    if declared:
        return declared
    relative = path.relative_to(root)
    if relative.parts[:2] == ("wiki", "sources"):
        return "source"
    if relative.parts[:2] == ("wiki", "concepts"):
        return "concept"
    if relative.parts[:2] == ("wiki", "projects"):
        return "project"
    if relative.parts[:2] == ("wiki", "derived"):
        return "derived"
    return "system"


def okf_type(note_type: str, source_path: Path, root: Path) -> str:
    if source_path.relative_to(root) == Path("AGENTS.md"):
        return "Wiki Schema"
    return {
        "source": "Research Source",
        "concept": "Research Concept",
        "project": "Research Project",
        "derived": "Derived Research Note",
        "system": "Wiki System Page",
    }.get(note_type, "Research Note")


def lifecycle_status(markdown_text: str, note_type: str) -> str:
    if note_type == "derived":
        return "draft"
    native = (
        scalar_field(markdown_text, "project_status")
        or scalar_field(markdown_text, "source_status")
        or scalar_field(markdown_text, "status")
        or ""
    ).lower()
    if native in {"draft", "planned", "planning", "partial", "failed", "pending"}:
        return "draft"
    if native in {"deprecated", "archived", "superseded"}:
        return "deprecated"
    return "stable"


def verification_event(markdown_text: str) -> dict[str, str] | None:
    actor = scalar_field(markdown_text, "okf_verified_by")
    verified_at = scalar_field(markdown_text, "okf_verified_at")
    if not actor or not verified_at:
        return None
    return {"by": actor, "at": verified_at}


def stale_after(markdown_text: str, note_type: str, days: int) -> str | None:
    if note_type != "project":
        return None
    project_status = (scalar_field(markdown_text, "project_status") or "").lower()
    if project_status != "active":
        return None
    snapshot = scalar_field(markdown_text, "snapshot_date")
    if not snapshot:
        return None
    try:
        snapshot_date = date.fromisoformat(snapshot[:10])
    except ValueError:
        return None
    stale_date = snapshot_date + timedelta(days=days)
    return datetime.combine(stale_date, time.min, timezone.utc).isoformat().replace("+00:00", "Z")


def strip_wikilink(value: str) -> tuple[str, str]:
    value = value.strip()
    if value.startswith("[[") and value.endswith("]]"):
        inner = value[2:-2]
        target, separator, label = inner.partition("|")
        return target.strip(), (label.strip() if separator else target.strip())
    return value, value


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def source_id(value: str) -> str:
    target, label = strip_wikilink(value)
    stem = Path(target).stem if "/" in target or "." in Path(target).name else label
    prefix = slugify(stem)[:48] or "source"
    return f"{prefix}-{short_hash(value)}"


def markdown_target(value: str) -> str:
    if any(character.isspace() for character in value) or any(character in value for character in "()"):
        return f"<{value}>"
    return value


def relative_repo_resource(root: Path, destination: Path, native_resource: str, okf_root: Path) -> str:
    candidate = Path(os.path.expanduser(native_resource))
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.exists():
        start = (okf_root / destination).parent
        return Path(os.path.relpath(candidate.resolve(), start=start.resolve())).as_posix()
    return native_resource


def record_lookup_values(record: dict[str, object]) -> set[str]:
    values = {str(record["title"]), Path(record["native_path"]).stem}
    values.update(str(value) for value in record.get("aliases", []))
    return {value.strip().lower() for value in values if value.strip()}


def build_records(root: Path, okf_root: Path, active_project_stale_days: int) -> list[dict[str, object]]:
    records = []
    for source_path in collect_native_documents(root):
        markdown_text = read_text(source_path)
        note_type = note_type_for(source_path, markdown_text, root)
        native_sources = list_field(markdown_text, "sources")
        if note_type == "derived" and not native_sources:
            native_sources = list_field(markdown_text, "context_files")
        destination = destination_for(root, source_path)
        records.append(
            {
                "source_path": source_path,
                "native_path": source_path.relative_to(root).as_posix(),
                "path": destination.as_posix(),
                "id": destination.with_suffix("").as_posix(),
                "title": detect_title(markdown_text, source_path),
                "description": description_for(markdown_text, note_type),
                "note_type": note_type,
                "type": okf_type(note_type, source_path, root),
                "status": lifecycle_status(markdown_text, note_type),
                "stale_after": stale_after(markdown_text, note_type, active_project_stale_days),
                "generated_at": file_timestamp(source_path),
                "aliases": list_field(markdown_text, "aliases"),
                "tags": list_field(markdown_text, "tags"),
                "native_sources": native_sources,
                "markdown_text": markdown_text,
            }
        )

    lookup: dict[str, dict[str, object]] = {}
    raw_to_source: dict[str, dict[str, object]] = {}
    native_path_to_record = {str(record["native_path"]): record for record in records}
    for record in records:
        for key in record_lookup_values(record):
            lookup.setdefault(key, record)
        if record["note_type"] == "source":
            for value in record["native_sources"]:
                raw_to_source.setdefault(str(value), record)

    for record in records:
        markdown_text = str(record["markdown_text"])
        destination = Path(str(record["path"]))
        provenance = []
        seen_resources = set()
        for value in record["native_sources"]:
            raw_value = str(value)
            target, label = strip_wikilink(raw_value)
            linked = lookup.get(target.lower()) or lookup.get(label.lower()) or native_path_to_record.get(target)
            if not linked and raw_value in raw_to_source and raw_to_source[raw_value] is not record:
                linked = raw_to_source[raw_value]
            if linked and linked is not record:
                resource = f"/{linked['path']}"
                title = str(linked["title"])
                entry_id = scalar_field(str(linked["markdown_text"]), "source_id") or source_id(raw_value)
                modified = None
                author = None
            else:
                resource = relative_repo_resource(root, destination, target, okf_root)
                title = label if target.startswith("[[") else Path(target).stem or label
                entry_id = source_id(raw_value)
                candidate = Path(os.path.expanduser(target))
                if not candidate.is_absolute():
                    candidate = root / candidate
                modified = file_timestamp(candidate) if candidate.is_file() else None
                author_name = scalar_field(markdown_text, "lead_author") if record["note_type"] == "source" else None
                author = f"human:{slugify(author_name)}" if author_name else None
            if resource in seen_resources:
                continue
            seen_resources.add(resource)
            entry = {"id": entry_id, "resource": resource, "title": title}
            if author:
                entry["author"] = author
            if modified:
                entry["last_modified"] = modified
            provenance.append(entry)
        record["sources"] = provenance

        if record["note_type"] == "source" and provenance:
            record["resource"] = provenance[0]["resource"]
        else:
            record["resource"] = None

        related_paths = []
        for value in list_field(markdown_text, "related") + list_field(markdown_text, "subprojects"):
            target, label = strip_wikilink(value)
            linked = lookup.get(target.lower()) or lookup.get(label.lower())
            if linked:
                related_paths.append(f"/{linked['path']}")
        record["related"] = list(dict.fromkeys(related_paths))

    return sorted(records, key=lambda item: (COLLECTIONS.index(Path(str(item["path"])).parts[0]), str(item["title"]).lower()))


def normalize_anchor(anchor: str) -> str:
    return f"#{slugify(anchor)}" if anchor else ""


def convert_wikilink(
    raw: str,
    embedded: bool,
    title_lookup: dict[str, dict[str, object]],
) -> str:
    target_part, separator, label_part = raw.partition("|")
    target_part = target_part.strip()
    label = (label_part.strip() if separator else target_part).strip()
    target_name, anchor_separator, anchor = target_part.partition("#")
    linked = title_lookup.get(target_name.lower())
    if linked:
        href = f"/{linked['path']}{normalize_anchor(anchor) if anchor_separator else ''}"
    else:
        unresolved = slugify(target_name) or "unresolved"
        href = f"/unresolved/{unresolved}.md{normalize_anchor(anchor) if anchor_separator else ''}"
    prefix = "!" if embedded else ""
    return f"{prefix}[{label}]({href})"


def rewrite_markdown_target(
    raw_target: str,
    native_path: Path,
    destination: Path,
    root: Path,
    okf_root: Path,
    source_to_destination: dict[Path, Path],
) -> str:
    wrapped = raw_target.startswith("<") and raw_target.endswith(">")
    target = raw_target[1:-1] if wrapped else raw_target
    if target.startswith(("http://", "https://", "mailto:", "tel:", "#", "/")):
        return raw_target
    if re.search(r"\s+[\"'].*[\"']$", target):
        return raw_target
    path_part, separator, anchor = target.partition("#")
    candidate = (native_path.parent / unquote(path_part)).resolve()
    mapped = source_to_destination.get(candidate)
    if mapped:
        rewritten = f"/{mapped.as_posix()}{normalize_anchor(anchor) if separator else ''}"
        return rewritten
    if candidate.exists():
        physical_destination = okf_root / destination
        relative = Path(os.path.relpath(candidate, start=physical_destination.parent.resolve())).as_posix()
        if separator:
            relative += normalize_anchor(anchor)
        return markdown_target(relative)
    return raw_target


def normalize_body_links(
    body: str,
    native_path: Path,
    destination: Path,
    root: Path,
    okf_root: Path,
    title_lookup: dict[str, dict[str, object]],
    source_to_destination: dict[Path, Path],
) -> str:
    lines = []
    in_fence = False
    fence_marker = ""
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue

        converted_segments = []
        for segment in re.split(r"(`+[^`]*`+)", line):
            if segment.startswith("`") and segment.endswith("`"):
                converted_segments.append(segment)
                continue
            converted = WIKILINK_RE.sub(
                lambda match: convert_wikilink(match.group(2), bool(match.group(1)), title_lookup),
                segment,
            )
            converted = MARKDOWN_LINK_RE.sub(
                lambda match: (
                    f"{match.group('label')}("
                    f"{rewrite_markdown_target(match.group('target'), native_path, destination, root, okf_root, source_to_destination)}"
                    ")"
                ),
                converted,
            )
            converted_segments.append(converted)
        lines.append("".join(converted_segments))
    return "\n".join(lines).rstrip() + "\n"


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def scalar_line(key: str, value: object) -> str:
    if isinstance(value, int):
        return f"{key}: {value}"
    return f"{key}: {json_value(value)}"


def render_frontmatter(record: dict[str, object]) -> str:
    markdown_text = str(record["markdown_text"])
    lines = [
        "---",
        scalar_line("type", record["type"]),
        scalar_line("title", record["title"]),
        scalar_line("description", record["description"]),
    ]
    if record.get("resource"):
        lines.append(scalar_line("resource", record["resource"]))
    if record.get("tags"):
        lines.append(scalar_line("tags", record["tags"]))
    lines.append(scalar_line("status", record["status"]))
    if record.get("stale_after"):
        lines.append(scalar_line("stale_after", record["stale_after"]))
    lines.append(scalar_line("generated", {"by": PRODUCER, "at": record["generated_at"]}))
    verified = verification_event(markdown_text)
    if verified:
        lines.append(scalar_line("verified", verified))
    if record.get("sources"):
        lines.append("sources:")
        lines.extend(f"  - {json_value(source)}" for source in record["sources"])

    extensions: list[tuple[str, object] | None] = [
        ("native_path", record["native_path"]),
        ("native_note_type", record["note_type"]),
        ("native_schema_version", scalar_field(markdown_text, "schema_version")),
        ("aliases", record.get("aliases") or None),
        ("source_id", scalar_field(markdown_text, "source_id")),
        ("citation_key", scalar_field(markdown_text, "citation_key")),
        ("source_kind", scalar_field(markdown_text, "source_kind")),
        ("source_status", scalar_field(markdown_text, "source_status")),
        ("year", int(scalar_field(markdown_text, "year"))) if (scalar_field(markdown_text, "year") or "").isdigit() else None,
        ("lead_author", scalar_field(markdown_text, "lead_author")),
        ("authors", list_field(markdown_text, "authors") or None),
        ("concept_group", scalar_field(markdown_text, "concept_group")),
        ("source_count", int(scalar_field(markdown_text, "source_count"))) if (scalar_field(markdown_text, "source_count") or "").isdigit() else None,
        ("project_id", scalar_field(markdown_text, "project_id")),
        ("project_name", scalar_field(markdown_text, "project_name")),
        ("project_level", scalar_field(markdown_text, "project_level")),
        ("parent_project_id", scalar_field(markdown_text, "parent_project_id")),
        ("project_status", scalar_field(markdown_text, "project_status")),
        ("snapshot_date", scalar_field(markdown_text, "snapshot_date")),
        ("context_mode", scalar_field(markdown_text, "context_mode")),
        ("related", record.get("related") or None),
    ]
    for extension in extensions:
        if extension is None:
            continue
        key, value = extension
        if value is not None and value != "":
            lines.append(scalar_line(key, value))
    lines.extend(["---", ""])
    return "\n".join(lines)


def render_document(
    record: dict[str, object],
    root: Path,
    okf_root: Path,
    title_lookup: dict[str, dict[str, object]],
    source_to_destination: dict[Path, Path],
) -> str:
    body = normalize_body_links(
        strip_frontmatter(str(record["markdown_text"])),
        Path(record["source_path"]),
        Path(str(record["path"])),
        root,
        okf_root,
        title_lookup,
        source_to_destination,
    )
    return render_frontmatter(record) + body


def render_collection_index(collection: str, records: list[dict[str, object]]) -> str:
    title = collection.title()
    descriptions = {
        "projects": "Research programmes and hierarchical subproject dossiers.",
        "concepts": "Cross-source synthesis organized as reusable research concepts.",
        "sources": "One traceable knowledge document per source artifact.",
        "derived": "Durable answers and analyses produced from the wiki.",
        "system": "Schema, maintenance reports, and operating documentation.",
    }
    lines = [f"# {title}", "", descriptions[collection], ""]
    for record in sorted(records, key=lambda item: str(item["title"]).lower()):
        filename = Path(str(record["path"])).name
        lines.append(f"* [{record['title']}]({filename}) - {record['description']}")
    return "\n".join(lines).rstrip() + "\n"


def render_root_index(records: list[dict[str, object]], summary: dict[str, object]) -> str:
    counts = summary["collections"]
    lines = [
        "---",
        f'okf_version: "{OKF_VERSION}"',
        "---",
        "",
        "# Research Wiki Knowledge Bundle",
        "",
        "A portable, agent-readable export of the local research wiki. The native Obsidian vault remains the authoring interface; this bundle is the interoperable exchange layer.",
        "",
        "## Collections",
        "",
    ]
    descriptions = {
        "projects": "programme status, evidence, milestones, and subprojects",
        "concepts": "cross-source synthesis and research themes",
        "sources": "traceable cards linked to immutable source artifacts",
        "derived": "durable question-answering and analysis outputs",
        "system": "schema and maintenance documentation",
    }
    for collection in COLLECTIONS:
        lines.append(f"* [{collection.title()}]({collection}/) - {counts[collection]} documents; {descriptions[collection]}.")
    lines.extend(
        [
            "",
            "## Trust And Freshness",
            "",
            f"* Format conformance: **{'valid' if summary['conformant'] else 'invalid'}** for OKF v{OKF_VERSION}.",
            f"* Trust events: {summary['trust']['human_reviewed']} human-reviewed, {summary['trust']['machine_confirmed']} machine-confirmed, {summary['trust']['unverified']} unverified.",
            f"* Freshness: {summary['stale_documents']} documents are beyond an explicit `stale_after` date.",
            "* Trust tiers report recorded verification events only; a completed manuscript is not silently treated as human verification.",
            "",
            "## Bundle Files",
            "",
            "* [Update log](log.md) - normalized, newest-first wiki activity.",
            "* `manifest.json` - machine-readable documents, relationships, hashes, and derived trust state.",
            "* `conformance.json` - deterministic OKF structure and link audit.",
            "",
        ]
    )
    return "\n".join(lines)


def native_log_entries(root: Path) -> dict[str, list[tuple[str, str]]]:
    config = load_config(root)
    log_path = root / config.get("log_path", "wiki/LOG.md")
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    if not log_path.exists():
        return grouped
    for line in read_text(log_path).splitlines():
        match = LOG_ENTRY_RE.match(line)
        if not match:
            continue
        day = match.group("timestamp")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            continue
        grouped[day].append((match.group("category").strip().title(), match.group("title").strip()))
    return grouped


def render_log(root: Path, generated_at: str, document_count: int) -> str:
    grouped = native_log_entries(root)
    today = generated_at[:10]
    grouped[today].insert(0, ("Export", f"Generated a conformant OKF v{OKF_VERSION} bundle with {document_count} concepts."))
    lines = ["# Research Wiki Update Log", ""]
    for day in sorted(grouped, reverse=True):
        lines.extend([f"## {day}"])
        for category, title in grouped[day]:
            lines.append(f"* **{category}**: {title}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_frontmatter_subset(markdown_text: str) -> dict[str, object]:
    block = frontmatter_text(markdown_text)
    parsed: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in block.splitlines():
        if raw_line.startswith("  - ") and current_list:
            value = raw_line[4:].strip()
            try:
                item = json.loads(value)
            except json.JSONDecodeError:
                item = value.strip('"\'')
            parsed.setdefault(current_list, [])
            assert isinstance(parsed[current_list], list)
            parsed[current_list].append(item)
            continue
        current_list = None
        if not raw_line or raw_line[0].isspace() or ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        value = value.strip()
        if not value:
            parsed[key] = []
            current_list = key
            continue
        try:
            parsed[key] = json.loads(value)
        except json.JSONDecodeError:
            parsed[key] = value.strip('"\'')
    return parsed


def is_valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def markdown_links(markdown_text: str) -> list[str]:
    return [match.group("target").strip("<>").split()[0] for match in MARKDOWN_LINK_RE.finditer(markdown_text)]


def validate_okf_bundle(bundle_root: Path, now: datetime | None = None) -> dict[str, object]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checked = 0
    broken_links = []
    now = now or datetime.now(timezone.utc)
    for path in sorted(bundle_root.rglob("*.md")):
        relative = path.relative_to(bundle_root)
        text = read_text(path)
        checked += 1
        if path.name == "index.md":
            if relative == Path("index.md"):
                metadata = parse_frontmatter_subset(text)
                if metadata.get("okf_version") != OKF_VERSION:
                    errors.append({"path": relative.as_posix(), "message": f"Root index must declare okf_version {OKF_VERSION}."})
            if not re.search(r"^#\s+\S", strip_frontmatter(text), re.MULTILINE):
                errors.append({"path": relative.as_posix(), "message": "Index has no section heading."})
            continue
        if path.name == "log.md":
            headings = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
            if not headings:
                errors.append({"path": relative.as_posix(), "message": "Log has no ISO date headings."})
            elif headings != sorted(headings, reverse=True):
                errors.append({"path": relative.as_posix(), "message": "Log date headings are not newest first."})
            continue

        metadata = parse_frontmatter_subset(text)
        if not frontmatter_text(text):
            errors.append({"path": relative.as_posix(), "message": "Missing YAML frontmatter."})
            continue
        if not str(metadata.get("type") or "").strip():
            errors.append({"path": relative.as_posix(), "message": "Missing non-empty type."})
        generated = metadata.get("generated")
        if generated is not None:
            if not isinstance(generated, dict) or not generated.get("by") or not is_valid_timestamp(generated.get("at")):
                errors.append({"path": relative.as_posix(), "message": "generated must contain by and an offset-aware ISO timestamp."})
        stale = metadata.get("stale_after")
        if stale is not None and not is_valid_timestamp(stale):
            errors.append({"path": relative.as_posix(), "message": "stale_after must be an offset-aware ISO timestamp."})
        sources = metadata.get("sources", [])
        if sources and (
            not isinstance(sources, list)
            or any(not isinstance(item, dict) or not item.get("resource") for item in sources)
        ):
            errors.append({"path": relative.as_posix(), "message": "Every sources entry must contain resource."})

        for target in markdown_links(strip_frontmatter(text)):
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            path_part = unquote(target.split("#", 1)[0])
            if not path_part.endswith(".md"):
                continue
            candidate = (bundle_root / path_part.lstrip("/")) if path_part.startswith("/") else (path.parent / path_part)
            candidate = candidate.resolve()
            try:
                candidate.relative_to(bundle_root.resolve())
            except ValueError:
                continue
            if not candidate.exists():
                broken_links.append({"source": relative.as_posix(), "target": target})

    for link in broken_links:
        warnings.append({"path": link["source"], "message": f"Broken internal link: {link['target']}"})
    return {
        "okf_version": OKF_VERSION,
        "valid": not errors,
        "documents_checked": checked,
        "errors": errors,
        "warnings": warnings,
        "broken_internal_links": broken_links,
        "validated_at": utc_timestamp(now.timestamp()),
    }


def trust_tier(metadata: dict[str, object]) -> str:
    verified = metadata.get("verified")
    if not verified:
        return "unverified"
    events = verified if isinstance(verified, list) else [verified]
    if any(isinstance(event, dict) and str(event.get("by", "")).startswith("human:") for event in events):
        return "human-reviewed"
    return "machine-confirmed"


def resolve_bundle_target(bundle_root: Path, source_path: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
        return None
    target_path = unquote(target.split("#", 1)[0])
    if not target_path.endswith(".md"):
        return None
    candidate = bundle_root / target_path.lstrip("/") if target_path.startswith("/") else source_path.parent / target_path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(bundle_root.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def build_manifest(bundle_root: Path, records: list[dict[str, object]], generated_at: str, conformance: dict[str, object]) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    documents = []
    path_to_id = {str(record["path"]): str(record["id"]) for record in records}
    edges = set()
    for record in records:
        path = bundle_root / str(record["path"])
        text = read_text(path)
        metadata = parse_frontmatter_subset(text)
        tier = trust_tier(metadata)
        stale_value = metadata.get("stale_after")
        is_stale = bool(stale_value and is_valid_timestamp(stale_value) and now >= datetime.fromisoformat(str(stale_value).replace("Z", "+00:00")))
        outbound = []
        for target in markdown_links(strip_frontmatter(text)):
            resolved = resolve_bundle_target(bundle_root, path, target)
            if not resolved:
                continue
            relative_target = resolved.relative_to(bundle_root).as_posix()
            if relative_target in RESERVED_FILENAMES or relative_target.endswith("/index.md"):
                continue
            target_id = path_to_id.get(relative_target)
            if target_id:
                outbound.append(target_id)
                edges.add((str(record["id"]), target_id, "link"))
        for source in metadata.get("sources", []):
            if not isinstance(source, dict):
                continue
            resolved = resolve_bundle_target(bundle_root, path, str(source.get("resource", "")))
            if not resolved:
                continue
            target_id = path_to_id.get(resolved.relative_to(bundle_root).as_posix())
            if target_id:
                edges.add((str(record["id"]), target_id, "source"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        documents.append(
            {
                "id": record["id"],
                "path": record["path"],
                "native_path": record["native_path"],
                "type": record["type"],
                "title": record["title"],
                "description": record["description"],
                "status": record["status"],
                "trust_tier": tier,
                "stale_after": stale_value,
                "stale": is_stale,
                "generated_at": record["generated_at"],
                "provenance_sources": len(metadata.get("sources", [])),
                "outbound_links": sorted(set(outbound)),
                "sha256": digest,
            }
        )
    edge_records = [
        {"source": source, "target": target, "kind": kind}
        for source, target, kind in sorted(edges)
    ]
    trust_counts = {
        "unverified": sum(item["trust_tier"] == "unverified" for item in documents),
        "machine_confirmed": sum(item["trust_tier"] == "machine-confirmed" for item in documents),
        "human_reviewed": sum(item["trust_tier"] == "human-reviewed" for item in documents),
    }
    collections = {
        collection: sum(Path(str(item["path"])).parts[0] == collection for item in records)
        for collection in COLLECTIONS
    }
    summary = {
        "documents": len(documents),
        "relationships": len(edge_records),
        "provenance_sources": sum(int(item["provenance_sources"]) for item in documents),
        "stale_documents": sum(bool(item["stale"]) for item in documents),
        "trust": trust_counts,
        "collections": collections,
        "conformant": bool(conformance["valid"]),
    }
    return {
        "format": "Open Knowledge Format",
        "okf_version": OKF_VERSION,
        "producer": PRODUCER,
        "generated_at": generated_at,
        "summary": summary,
        "documents": documents,
        "relationships": edge_records,
    }


def write_archive(bundle_root: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle_root.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("research-wiki-okf") / path.relative_to(bundle_root)).as_posix())


def export_okf(root: Path) -> dict[str, object]:
    root = root.resolve()
    config = load_config(root)
    bundle_root = root / config.get("okf_dir", "output/okf")
    archive_path = root / config.get("okf_archive", "output/research-wiki-okf.zip")
    stale_days = int(config.get("okf_active_project_stale_days", 90))
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    records = build_records(root, bundle_root, stale_days)
    title_lookup: dict[str, dict[str, object]] = {}
    source_to_destination: dict[Path, Path] = {}
    for record in records:
        for value in record_lookup_values(record):
            title_lookup.setdefault(value, record)
        source_to_destination[Path(record["source_path"]).resolve()] = Path(str(record["path"]))
    title_lookup.update(
        {
            "derived notes": {"path": "derived/index.md"},
            "project catalog": {"path": "projects/index.md"},
            "projects": {"path": "projects/index.md"},
        }
    )

    for record in records:
        destination = bundle_root / str(record["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            render_document(record, root, bundle_root, title_lookup, source_to_destination),
            encoding="utf-8",
        )

    for collection in COLLECTIONS:
        members = [record for record in records if Path(str(record["path"])).parts[0] == collection]
        collection_dir = bundle_root / collection
        collection_dir.mkdir(parents=True, exist_ok=True)
        (collection_dir / "index.md").write_text(render_collection_index(collection, members), encoding="utf-8")

    generated_at = utc_timestamp()
    (bundle_root / "log.md").write_text(render_log(root, generated_at, len(records)), encoding="utf-8")
    preliminary = validate_okf_bundle(bundle_root)
    manifest = build_manifest(bundle_root, records, generated_at, preliminary)
    (bundle_root / "index.md").write_text(render_root_index(records, manifest["summary"]), encoding="utf-8")
    conformance = validate_okf_bundle(bundle_root)
    manifest = build_manifest(bundle_root, records, generated_at, conformance)
    (bundle_root / "index.md").write_text(render_root_index(records, manifest["summary"]), encoding="utf-8")
    (bundle_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (bundle_root / "conformance.json").write_text(json.dumps(conformance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_archive(bundle_root, archive_path)

    return {
        "bundle_root": bundle_root.relative_to(root).as_posix(),
        "entrypoint": (bundle_root / "index.md").relative_to(root).as_posix(),
        "manifest_path": (bundle_root / "manifest.json").relative_to(root).as_posix(),
        "conformance_path": (bundle_root / "conformance.json").relative_to(root).as_posix(),
        "archive_path": archive_path.relative_to(root).as_posix(),
        "documents": len(records),
        "relationships": len(manifest["relationships"]),
        "conformance": conformance,
        "summary": manifest["summary"],
        "manifest": manifest,
    }


def export_okf_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the research wiki as an OKF v0.2 knowledge bundle.")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    result = export_okf(parse_root_arg(args.root))
    printable = {key: value for key, value in result.items() if key != "manifest"}
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    return 0 if result["conformance"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(export_okf_main())
