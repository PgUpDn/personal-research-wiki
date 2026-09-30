#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

from export_okf import export_okf
from wiki_pipeline import detect_title, load_config, note_blurb, parse_root_arg, read_text, slugify, strip_frontmatter


EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:")

from wiki_theme import icon, render_workspace_shell

STYLE_CSS = Path(__file__).with_name("wiki_theme.css").read_text(encoding="utf-8")


def parse_aliases(markdown_text: str) -> list[str]:
    return parse_list_field(markdown_text, "aliases")


def frontmatter_lines(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    collected = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        collected.append(line)
    return collected


def parse_scalar_field(markdown_text: str, field_name: str) -> str | None:
    for line in frontmatter_lines(markdown_text):
        match = re.match(rf"^{re.escape(field_name)}:\s*(.+)$", line)
        if not match:
            continue
        raw = match.group(1).strip()
        if raw in {"[]", "\"\"", "''"}:
            return None
        return raw.strip("\"'")
    return None


def parse_list_field(markdown_text: str, field_name: str) -> list[str]:
    items = []
    lines = frontmatter_lines(markdown_text)
    in_field = False
    for line in lines:
        if not in_field:
            if re.match(rf"^{re.escape(field_name)}:\s*$", line):
                in_field = True
            continue
        if re.match(r"^\s*-\s+", line):
            raw = re.sub(r"^\s*-\s+", "", line).strip()
            items.append(raw.strip("\"'"))
            continue
        if line.strip() and not line.startswith(" "):
            break
    return items


def parse_bullet_value(markdown_text: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", strip_frontmatter(markdown_text), re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def compact_text(value: str, limit: int = 2400) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit]


def extract_section_excerpt(markdown_text: str, headings: tuple[str, ...], limit: int = 220) -> str | None:
    body = strip_frontmatter(markdown_text)
    lines = body.splitlines()
    normalized_targets = {heading.strip().lower() for heading in headings}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip().lower()
        if heading not in normalized_targets:
            continue
        excerpt_lines = []
        for candidate in lines[index + 1:]:
            current = candidate.strip()
            if not current:
                if excerpt_lines:
                    break
                continue
            if current.startswith("#"):
                break
            if current.startswith(">"):
                continue
            if re.match(r"^[-*]\s+(source id|citation key|source kind|status|raw source|working text cache|page image directory|page count|year|venue|doi|arxiv|lead author|authors)\b", current, re.IGNORECASE):
                continue
            excerpt_lines.append(current)
            if len(" ".join(excerpt_lines)) >= limit * 2:
                break
        if excerpt_lines:
            return compact_text(" ".join(excerpt_lines), limit=limit)
    return None


def search_summary(markdown_text: str) -> str:
    note_type = parse_scalar_field(markdown_text, "note_type")
    if note_type == "source":
        preferred = extract_section_excerpt(markdown_text, ("TL;DR", "Abstract"))
        if preferred:
            return preferred
    return note_blurb(markdown_text)


def collect_export_docs(root: Path) -> list[Path]:
    config = load_config(root)
    wiki_dir = root / config["wiki_dir"]
    docs = sorted(path for path in wiki_dir.glob("*.md") if path.is_file())
    docs.extend(sorted((root / config["source_notes_dir"]).glob("*.md")))
    docs.extend(sorted((root / config["concepts_dir"]).glob("*.md")))
    docs.extend(sorted((root / config.get("projects_dir", "wiki/projects")).glob("*.md")))
    docs.extend(sorted((root / config["derived_wiki_dir"]).glob("*.md")))
    agents_path = root / config["schema_path"]
    if agents_path.exists():
        docs.append(agents_path)
    return docs


def export_relpath(root: Path, source_path: Path) -> Path:
    rel = source_path.relative_to(root)
    if rel.as_posix() == "wiki/INDEX.md":
        return Path("index.html")
    if rel.parts[0] == "wiki":
        return Path(*rel.parts[1:]).with_suffix(".html")
    return rel.with_suffix(".html")


def nav_group_for(export_path: Path) -> str:
    if export_path.parent == Path("."):
        return "System"
    if export_path.parts[0] == "sources":
        return "Sources"
    if export_path.parts[0] == "concepts":
        return "Concepts"
    if export_path.parts[0] == "projects":
        return "Projects"
    if export_path.parts[0] == "derived":
        return "Derived"
    return "Other"


def build_doc_index(root: Path) -> tuple[list[dict[str, object]], dict[str, Path], dict[Path, Path]]:
    docs = []
    title_to_export: dict[str, Path] = {}
    source_to_export: dict[Path, Path] = {}
    for path in collect_export_docs(root):
        text = read_text(path)
        title = detect_title(text, path)
        aliases = parse_aliases(text)
        export_path = export_relpath(root, path)
        source_to_export[path.resolve()] = export_path
        doc = {
            "source_path": path,
            "export_path": export_path,
            "title": title,
            "aliases": aliases,
            "group": nav_group_for(export_path),
            "text": text,
            "note_type": parse_scalar_field(text, "note_type") or nav_group_for(export_path).lower(),
            "summary": search_summary(text),
            "last_compiled": parse_scalar_field(text, "last_compiled") or parse_bullet_value(text, "Last compiled"),
            "year": parse_scalar_field(text, "year"),
            "lead_author": parse_scalar_field(text, "lead_author"),
            "venue": parse_scalar_field(text, "venue"),
            "concept_group": parse_scalar_field(text, "concept_group"),
            "source_count": parse_scalar_field(text, "source_count"),
            "project_id": parse_scalar_field(text, "project_id"),
            "project_name": parse_scalar_field(text, "project_name"),
            "project_level": parse_scalar_field(text, "project_level"),
            "parent_project_id": parse_scalar_field(text, "parent_project_id"),
            "project_status": parse_scalar_field(text, "project_status"),
            "snapshot_date": parse_scalar_field(text, "snapshot_date"),
            "concepts": parse_list_field(text, "concepts"),
            "related": parse_list_field(text, "related"),
            "github_links": parse_list_field(text, "github_links"),
        }
        docs.append(doc)
        lookup_values = {title, path.stem, path.stem.upper(), path.stem.replace("_", " ")}
        lookup_values.update(aliases)
        for value in lookup_values:
            normalized = value.strip().lower()
            if normalized:
                title_to_export[normalized] = export_path
    docs.sort(key=lambda item: (item["group"], str(item["title"]).lower()))
    return docs, title_to_export, source_to_export


def build_search_index(root: Path, docs: list[dict[str, object]]) -> dict[str, object]:
    records = []
    for doc in docs:
        source_path = Path(doc["source_path"])
        export_path = Path(doc["export_path"])
        text = str(doc["text"])
        body = strip_frontmatter(text)
        aliases = parse_aliases(text)
        summary = search_summary(text)
        note_type = parse_scalar_field(text, "note_type") or nav_group_for(export_path).lower()
        year = parse_scalar_field(text, "year")
        venue = parse_scalar_field(text, "venue")
        doi = parse_scalar_field(text, "doi")
        arxiv_id = parse_scalar_field(text, "arxiv_id")
        project_id = parse_scalar_field(text, "project_id")
        project_level = parse_scalar_field(text, "project_level")
        parent_project_id = parse_scalar_field(text, "parent_project_id")
        project_status = parse_scalar_field(text, "project_status")
        github_links = parse_list_field(text, "github_links")
        searchable = " ".join(
            part
            for part in [
                str(doc["title"]),
                " ".join(aliases),
                summary,
                note_type,
                str(doc["group"]),
                year or "",
                venue or "",
                doi or "",
                arxiv_id or "",
                project_id or "",
                project_level or "",
                parent_project_id or "",
                project_status or "",
                " ".join(github_links),
                source_path.relative_to(root).as_posix(),
                compact_text(body, limit=60000),  # body cap: only INDEX.md (143k chars) is truncated
            ]
            if part
        )
        records.append(
            {
                "title": str(doc["title"]),
                "href": export_path.as_posix(),
                "path": source_path.relative_to(root).as_posix(),
                "group": str(doc["group"]),
                "note_type": note_type,
                "aliases": aliases,
                "summary": summary,
                "year": year,
                "venue": venue,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "project_id": project_id,
                "project_level": project_level,
                "parent_project_id": parent_project_id,
                "project_status": project_status,
                "github_links": github_links,
                "search_text": searchable.lower(),
            }
        )
    return {"documents": records}


def json_for_html(data: object) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def heading_anchor(text: str) -> str:
    return slugify(text) or "section"


def coerce_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else 0


def parse_wikilink(value: str) -> tuple[str, str]:
    raw = value.strip().strip("\"'")
    if raw.startswith("[[") and raw.endswith("]]"):
        inner = raw[2:-2]
        target, _, label = inner.partition("|")
        target = target.strip()
        label = (label or target.split("#", 1)[0]).strip()
        return target, label
    return raw, raw


def render_tag_link(target: str, label: str, current_export_path: Path, title_to_export: dict[str, Path]) -> str:
    href = resolve_wikilink(target, current_export_path, title_to_export)
    if href == "#":
        return f'<span class="tag">{html.escape(label)}</span>'
    return f'<a class="tag" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'


def render_doc_tags(values: list[str], current_export_path: Path, title_to_export: dict[str, Path], limit: int = 3) -> str:
    chips = []
    for value in values[:limit]:
        target, label = parse_wikilink(value)
        chips.append(render_tag_link(target, label, current_export_path, title_to_export))
    if not chips:
        return ""
    return f'<div class="tag-row">{"".join(chips)}</div>'


def summarize_text(value: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def home_project_excerpt(markdown_text: str) -> str:
    body = strip_frontmatter(markdown_text)
    match = re.search(r"^-\s+\*\*What it is\*\*:\s*(.+)$", body, re.MULTILINE | re.IGNORECASE)
    excerpt = match.group(1) if match else extract_section_excerpt(markdown_text, ("Programme Thesis", "Project Thesis"), 350)
    if not excerpt:
        return ""
    excerpt = re.sub(r"\[\[([^]|]+)(?:\|([^]]+))?\]\]", lambda found: found.group(2) or found.group(1), excerpt)
    excerpt = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", excerpt)
    excerpt = re.sub(r"[`*_]", "", excerpt)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    first_sentence = re.split(r"(?<=[.!?])\s+", excerpt, maxsplit=1)[0]
    return summarize_text(first_sentence, 185)


def source_modified_at(root: Path, doc: dict[str, object]) -> float:
    for source in parse_list_field(str(doc["text"]), "sources"):
        if not source.startswith(("raw/", "Clippings/")):
            continue
        path = root / source
        if path.is_file():
            return path.stat().st_mtime
    return 0.0


def home_source_title(doc: dict[str, object]) -> str:
    title = str(doc["title"])
    if not title.isupper():
        return title
    for source in parse_list_field(str(doc["text"]), "sources"):
        filename = Path(source).stem
        match = re.match(r"^.+? - (?:19|20)\d{2} - (.+)$", filename)
        if match and len(match.group(1)) > len(title) * 1.15:
            return match.group(1)
    return title


def relative_href(target: Path, current_export_path: Path) -> str:
    return os.path.relpath(target, start=current_export_path.parent).replace(os.sep, "/")


def copy_asset(source_abs: Path, root: Path, export_root: Path) -> Path:
    try:
        rel = source_abs.resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(source_abs.name)
    destination_rel = Path("_files") / rel
    destination = export_root / destination_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_abs, destination)
    return destination_rel


def resolve_wikilink(target: str, current_export_path: Path, title_to_export: dict[str, Path]) -> str:
    page_target, _, anchor = target.partition("#")
    lookup = page_target.strip().lower()
    destination = title_to_export.get(lookup)
    if destination is None:
        return "#"
    href = relative_href(destination, current_export_path)
    if anchor:
        href += f"#{heading_anchor(anchor)}"
    return href


def resolve_markdown_target(
    raw_target: str,
    source_path: Path,
    current_export_path: Path,
    root: Path,
    export_root: Path,
    source_to_export: dict[Path, Path],
) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
        return target
    absolute = (source_path.parent / target).resolve()
    if absolute.suffix.lower() == ".md" and absolute in source_to_export:
        return relative_href(source_to_export[absolute], current_export_path)
    if absolute.exists():
        copied = copy_asset(absolute, root, export_root)
        return relative_href(copied, current_export_path)
    return html.escape(target, quote=True)


def convert_inline(
    text: str,
    source_path: Path,
    current_export_path: Path,
    root: Path,
    export_root: Path,
    title_to_export: dict[str, Path],
    source_to_export: dict[Path, Path],
) -> str:
    placeholders: dict[str, str] = {}

    def store(value: str) -> str:
        key = f"@@PLACEHOLDER{len(placeholders)}@@"
        placeholders[key] = value
        return key

    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", lambda match: store(f"<code>{html.escape(match.group(1))}</code>"), escaped)

    def replace_image(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1))
        href = resolve_markdown_target(html.unescape(match.group(2)), source_path, current_export_path, root, export_root, source_to_export)
        return store(f'<img src="{html.escape(href, quote=True)}" alt="{alt}">')

    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_image, escaped)

    def replace_md_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = resolve_markdown_target(html.unescape(match.group(2)), source_path, current_export_path, root, export_root, source_to_export)
        return store(f'<a href="{html.escape(href, quote=True)}">{label}</a>')

    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_md_link, escaped)

    def replace_wikilink(match: re.Match[str]) -> str:
        inner = html.unescape(match.group(1))
        target, _, label = inner.partition("|")
        href = resolve_wikilink(target, current_export_path, title_to_export)
        link_label = html.escape(label or target.split("#", 1)[0])
        return store(f'<a href="{html.escape(href, quote=True)}">{link_label}</a>')

    escaped = re.sub(r"\[\[([^\]]+)\]\]", replace_wikilink, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

    for key, value in placeholders.items():
        escaped = escaped.replace(key, value)
    return escaped


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$", line))


def parse_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def render_markdown_blocks(
    text: str,
    source_path: Path,
    current_export_path: Path,
    root: Path,
    export_root: Path,
    title_to_export: dict[str, Path],
    source_to_export: dict[Path, Path],
) -> str:
    lines = text.splitlines()
    blocks: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            fence = stripped[:3]
            language = stripped[3:].strip()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith(fence):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            class_attr = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            blocks.append(f"<pre><code{class_attr}>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            anchor = heading_anchor(heading_text)
            content = convert_inline(heading_text, source_path, current_export_path, root, export_root, title_to_export, source_to_export)
            blocks.append(f'<h{level} id="{anchor}">{content}</h{level}>')
            index += 1
            continue

        if re.fullmatch(r"[-*_]{3,}", stripped):
            blocks.append("<hr>")
            index += 1
            continue

        if stripped.startswith(">"):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[index]))
                index += 1
            inner = render_markdown_blocks("\n".join(quote_lines), source_path, current_export_path, root, export_root, title_to_export, source_to_export)
            blocks.append(f"<blockquote>{inner}</blockquote>")
            continue

        if stripped == "<details>":
            index += 1
            summary_text = "Details"
            if index < len(lines) and lines[index].strip().startswith("<summary>") and lines[index].strip().endswith("</summary>"):
                summary_line = lines[index].strip()
                summary_text = re.sub(r"^<summary>|</summary>$", "", summary_line).strip() or "Details"
                index += 1
            inner_lines = []
            while index < len(lines) and lines[index].strip() != "</details>":
                inner_lines.append(lines[index])
                index += 1
            if index < len(lines) and lines[index].strip() == "</details>":
                index += 1
            inner = render_markdown_blocks("\n".join(inner_lines), source_path, current_export_path, root, export_root, title_to_export, source_to_export)
            summary_html = convert_inline(summary_text, source_path, current_export_path, root, export_root, title_to_export, source_to_export)
            blocks.append(f"<details><summary>{summary_html}</summary>{inner}</details>")
            continue

        if "|" in stripped and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            headers = parse_table_row(lines[index])
            index += 2
            rows = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not candidate or "|" not in candidate:
                    break
                rows.append(parse_table_row(lines[index]))
                index += 1
            table = ["<table><thead><tr>"]
            table.extend(
                f"<th>{convert_inline(cell, source_path, current_export_path, root, export_root, title_to_export, source_to_export)}</th>"
                for cell in headers
            )
            table.append("</tr></thead><tbody>")
            for row in rows:
                table.append("<tr>")
                for cell in row:
                    table.append(
                        f"<td>{convert_inline(cell, source_path, current_export_path, root, export_root, title_to_export, source_to_export)}</td>"
                    )
                table.append("</tr>")
            table.append("</tbody></table>")
            blocks.append("".join(table))
            continue

        if re.match(r"^[-*]\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[index].strip())
                items.append(
                    f"<li>{convert_inline(item, source_path, current_export_path, root, export_root, title_to_export, source_to_export)}</li>"
                )
                index += 1
            blocks.append(f"<ul>{''.join(items)}</ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\s*\d+\.\s+", lines[index]):
                item = re.sub(r"^\s*\d+\.\s+", "", lines[index].strip())
                items.append(
                    f"<li>{convert_inline(item, source_path, current_export_path, root, export_root, title_to_export, source_to_export)}</li>"
                )
                index += 1
            blocks.append(f"<ol>{''.join(items)}</ol>")
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                index += 1
                break
            if (
                candidate.startswith("#")
                or candidate.startswith(">")
                or candidate.startswith("```")
                or re.match(r"^[-*]\s+", candidate)
                or re.match(r"^\d+\.\s+", candidate)
                or re.fullmatch(r"[-*_]{3,}", candidate)
                or (index + 1 < len(lines) and "|" in candidate and is_table_separator(lines[index + 1]))
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        paragraph = " ".join(paragraph_lines)
        blocks.append(
            f"<p>{convert_inline(paragraph, source_path, current_export_path, root, export_root, title_to_export, source_to_export)}</p>"
        )

    return "\n".join(blocks)


def collection_counts(docs: list[dict[str, object]]) -> dict[str, int]:
    return {
        "sources": sum(1 for doc in docs if doc["group"] == "Sources"),
        "concepts": sum(1 for doc in docs if doc["group"] == "Concepts"),
        "projects": sum(1 for doc in docs if doc["note_type"] == "project"),
        "derived": sum(1 for doc in docs if doc["group"] == "Derived"),
        "system": sum(1 for doc in docs if doc["group"] == "System"),
    }


def is_portal_page(export_path: Path) -> bool:
    return export_path in {Path("index.html"), Path("search.html"), Path("ask.html"), Path("knowledge.html")}


def find_doc(docs: list[dict[str, object]], export_path: str) -> dict[str, object] | None:
    target = Path(export_path)
    return next((doc for doc in docs if Path(doc["export_path"]) == target), None)


def render_portal_sidebar(docs: list[dict[str, object]], current_export_path: Path) -> str:
    counts = collection_counts(docs)
    overview_doc = find_doc(docs, "SYSTEM_OVERVIEW.html")
    lint_doc = find_doc(docs, "LINT_AND_HEAL.html")
    dashboard_doc = find_doc(docs, "DASHBOARD.html")
    projects_doc = find_doc(docs, "projects/README.html")
    home_href = relative_href(Path("index.html"), current_export_path)
    search_href = relative_href(Path("search.html"), current_export_path)
    ask_href = relative_href(Path("ask.html"), current_export_path)
    knowledge_href = relative_href(Path("knowledge.html"), current_export_path)
    parts = [
        '<div class="brand">',
        "<h1>Research Wiki</h1>",
        "<p>Compiled reference view of the local research vault.</p>",
        "</div>",
        '<div class="sidebar-summary">',
        f'<strong>{counts["sources"]}</strong> sources',
        " · ",
        f'<strong>{counts["concepts"]}</strong> concepts',
        " · ",
        f'<strong>{counts["projects"]}</strong> projects',
        " · ",
        f'<strong>{counts["derived"]}</strong> derived notes',
        "</div>",
        '<nav class="nav-group"><h2>Navigation</h2><ul>',
        f'<li><a class="{"current" if current_export_path == Path("index.html") else ""}" href="{html.escape(home_href, quote=True)}">Main Page</a></li>',
    ]
    if overview_doc:
        parts.append(
            f'<li><a href="{html.escape(relative_href(Path(overview_doc["export_path"]), current_export_path), quote=True)}">System Overview</a></li>'
        )
    if projects_doc:
        parts.append(
            f'<li><a href="{html.escape(relative_href(Path(projects_doc["export_path"]), current_export_path), quote=True)}">Projects</a></li>'
        )
    parts.append("</ul></nav>")
    parts.extend(
        [
            '<nav class="nav-group"><h2>Tools</h2><ul>',
            f'<li><a class="{"current" if current_export_path == Path("search.html") else ""}" href="{html.escape(search_href, quote=True)}">Search The Wiki</a></li>',
            f'<li><a class="{"current" if current_export_path == Path("ask.html") else ""}" href="{html.escape(ask_href, quote=True)}">Ask The Wiki</a></li>',
            f'<li><a class="{"current" if current_export_path == Path("knowledge.html") else ""}" href="{html.escape(knowledge_href, quote=True)}">Knowledge Map</a></li>',
            "</ul></nav>",
            '<nav class="nav-group"><h2>System</h2><ul>',
        ]
    )
    if dashboard_doc:
        parts.append(
            f'<li><a href="{html.escape(relative_href(Path(dashboard_doc["export_path"]), current_export_path), quote=True)}">Dashboard</a></li>'
        )
    if lint_doc:
        parts.append(
            f'<li><a href="{html.escape(relative_href(Path(lint_doc["export_path"]), current_export_path), quote=True)}">Health Checks</a></li>'
        )
    parts.append("</ul></nav>")
    return "\n".join(parts)


def render_sidebar(docs: list[dict[str, object]], current_export_path: Path) -> str:
    if is_portal_page(current_export_path):
        return render_portal_sidebar(docs, current_export_path)
    groups: dict[str, list[dict[str, object]]] = {"System": [], "Projects": [], "Sources": [], "Concepts": [], "Derived": [], "Other": []}
    for doc in docs:
        groups[str(doc["group"])].append(doc)

    search_current = " current" if current_export_path == Path("search.html") else ""
    ask_current = " current" if current_export_path == Path("ask.html") else ""
    knowledge_current = " current" if current_export_path == Path("knowledge.html") else ""
    home_href = relative_href(Path("index.html"), current_export_path)
    parts = [
        '<div class="brand">',
        f'<h1><a href="{html.escape(home_href, quote=True)}">Research Wiki</a></h1>',
        "<p>User-facing HTML export of the compiled vault.</p>",
        "</div>",
        '<div class="sidebar-actions">',
        f'<a class="search-link{search_current}" href="{html.escape(relative_href(Path("search.html"), current_export_path), quote=True)}">Search The Wiki</a>',
        f'<a class="search-link{ask_current}" href="{html.escape(relative_href(Path("ask.html"), current_export_path), quote=True)}">Ask The Wiki</a>',
        f'<a class="search-link{knowledge_current}" href="{html.escape(relative_href(Path("knowledge.html"), current_export_path), quote=True)}">Knowledge Map</a>',
        "</div>",
    ]
    for group_name in ("System", "Projects", "Sources", "Concepts", "Derived", "Other"):
        items = groups[group_name]
        if not items:
            continue
        group_class = slugify(group_name) or "other"
        parts.append(f'<nav class="nav-group nav-{group_class}"><h2>{html.escape(group_name)}</h2><ul>')
        for item in items:
            export_path = item["export_path"]
            href = relative_href(export_path, current_export_path)
            current = " current" if export_path == current_export_path else ""
            parts.append(
                f'<li><a class="{current.strip()}" href="{html.escape(href, quote=True)}">{html.escape(str(item["title"]))}</a></li>'
            )
        parts.append("</ul></nav>")
    return "\n".join(parts)


def render_index_page(
    doc: dict[str, object],
    docs: list[dict[str, object]],
    root: Path,
    export_root: Path,
    title_to_export: dict[str, Path],
    source_to_export: dict[Path, Path],
) -> str:
    del export_root, title_to_export, source_to_export
    export_path = Path("index.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    source_docs = [item for item in docs if item["group"] == "Sources"]
    concept_docs = [item for item in docs if item["group"] == "Concepts"]
    project_docs = [item for item in docs if item["note_type"] == "project"]
    counts = collection_counts(docs)
    overview_doc = find_doc(docs, "SYSTEM_OVERVIEW.html")
    last_compiled = str(doc.get("last_compiled") or (overview_doc or {}).get("last_compiled") or "Unknown")

    featured_sources = sorted(
        (item for item in source_docs if item.get("year")),
        key=lambda item: (-source_modified_at(root, item), str(item["title"]).lower()),
    )[:6]
    grouped_concepts: dict[str, list[dict[str, object]]] = defaultdict(list)
    for concept_doc in concept_docs:
        grouped_concepts[str(concept_doc.get("concept_group") or "Other")].append(concept_doc)
    ordered_groups = sorted(grouped_concepts.items(), key=lambda item: item[0].lower())
    for _, items in ordered_groups:
        items.sort(key=lambda item: (-coerce_int(item.get("source_count")), str(item["title"]).lower()))
    research_areas_html = []
    for group_name, items in ordered_groups:
        top_items = items[:3]
        links = []
        for item in top_items:
            href = relative_href(Path(item["export_path"]), export_path)
            links.append(
                f'<a href="{html.escape(href, quote=True)}">{html.escape(str(item["title"]))}</a>'
            )
        research_areas_html.append(
            f"""<article class="home-area-row">
  <div>
    <h3>{html.escape(group_name)}</h3>
    <p>{" · ".join(links)}</p>
  </div>
  <span class="home-area-count">{len(items)} topics</span>
</article>"""
        )

    featured_sources_html = []
    for source_doc in featured_sources:
        href = relative_href(Path(source_doc["export_path"]), export_path)
        meta_parts = [value for value in [source_doc.get("year"), source_doc.get("venue")] if value]
        meta_html = " · ".join(html.escape(str(part)) for part in meta_parts)
        display_title = home_source_title(source_doc)
        featured_sources_html.append(
            f"""<article class="home-source-row">
  <p class="home-source-meta">{meta_html}</p>
  <h3><a href="{html.escape(href, quote=True)}">{html.escape(display_title)}</a></h3>
</article>"""
        )

    project_groups = []
    programmes = sorted(
        (item for item in project_docs if not item.get("parent_project_id")),
        key=lambda item: str(item.get("project_name") or item["title"]).lower(),
    )
    for project_doc in programmes:
        project_id = str(project_doc.get("project_id") or "")
        name = str(project_doc.get("project_name") or project_doc["title"])
        display_name = re.sub(r"\s*\([^)]*\)$", "", name)
        href = relative_href(Path(project_doc["export_path"]), export_path)
        status = str(project_doc.get("project_status") or "active").capitalize()
        summary = home_project_excerpt(str(project_doc["text"]))
        children = sorted(
            (item for item in project_docs if str(item.get("parent_project_id") or "") == project_id),
            key=lambda item: str(item.get("project_name") or item["title"]).lower(),
        )
        child_rows = []
        for child in children:
            child_href = relative_href(Path(child["export_path"]), export_path)
            child_name = re.sub(r"\s*\([^)]*\)$", "", str(child.get("project_name") or child["title"]))
            child_status = str(child.get("project_status") or "active").capitalize()
            child_rows.append(
                f'<a class="home-subproject-row" href="{html.escape(child_href, quote=True)}">'
                f'<span>{html.escape(child_name.replace("_", " "))}</span>'
                f'<small>{html.escape(child_status)}</small>{icon("arrow")}</a>'
            )
        subprojects = (
            f'<div class="home-subprojects"><p class="home-subproject-heading">Subprojects</p>{"".join(child_rows)}</div>'
            if child_rows else ""
        )
        project_groups.append(
            f"""<section class="home-project-group">
  <div class="home-project-heading">
    <div><p class="home-project-status">{html.escape(status)}</p>
      <h3><a href="{html.escape(href, quote=True)}">{html.escape(display_name)}</a></h3></div>
    <a class="home-project-open" href="{html.escape(href, quote=True)}" aria-label="Open {html.escape(display_name, quote=True)}">{icon("arrow")}</a>
  </div>
  <p class="home-project-description">{html.escape(summary)}</p>
  {subprojects}
</section>"""
        )

    utility_links = []
    utility_pages = [
        ("System overview", overview_doc),
        ("Dashboard", find_doc(docs, "DASHBOARD.html")),
        ("Health checks", find_doc(docs, "LINT_AND_HEAL.html")),
        ("Project catalog", find_doc(docs, "projects/README.html")),
        ("Derived notes", find_doc(docs, "derived/README.html")),
    ]
    for label, utility_doc in utility_pages:
        if utility_doc:
            href = relative_href(Path(utility_doc["export_path"]), export_path)
            utility_links.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    utility_links.append('<a href="knowledge.html">Knowledge map</a>')

    return f"""<!doctype html>
<html lang="en">
<head>
  <script src="assets/wiki-ui.js" defer></script>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Wiki</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body class="workspace home-page">
  {render_workspace_shell(docs, export_path, "Overview")}

  <main class="home-main" id="main-content">
    <section class="home-intro">
      <div>
        <p class="home-kicker">Research workspace</p>
        <h1>Overview</h1>
        <p class="home-lede">Last compiled {html.escape(last_compiled)}</p>
      </div>
      <div class="home-actions">
        <a class="home-action" href="search.html">{icon("search")} Search library</a>
        <a class="home-action primary" href="ask.html">{icon("ask")} Ask the Wiki</a>
      </div>
    </section>

    <dl class="home-stats">
      <div class="home-stat"><dt>Sources</dt><dd>{counts["sources"]}</dd></div>
      <div class="home-stat"><dt>Concepts</dt><dd>{counts["concepts"]}</dd></div>
      <div class="home-stat"><dt>Projects</dt><dd>{counts["projects"]}</dd></div>
      <div class="home-stat"><dt>Research notes</dt><dd>{counts["derived"]}</dd></div>
    </dl>

    <section class="home-projects" id="projects">
      <div class="home-section-heading">
        <h2>Projects</h2>
        <a href="projects/README.html">Project catalog</a>
      </div>
      <div class="project-grid">{''.join(project_groups) if project_groups else '<p class="home-project-empty">No projects yet.</p>'}</div>
    </section>

    <div class="home-dashboard">
      <section class="home-section" id="research-areas">
        <div class="home-section-heading">
          <h2>Research areas</h2>
          <a href="search.html?group=Concepts">All concepts</a>
        </div>
        {''.join(research_areas_html)}
      </section>

      <section class="home-section" id="recent-sources">
        <div class="home-section-heading">
          <h2>Recently added</h2>
          <a href="search.html">View all {counts["sources"]}</a>
        </div>
        {''.join(featured_sources_html)}
      </section>
    </div>

    <nav class="home-utility" aria-label="System pages">
      <strong>System</strong>
      {''.join(utility_links)}
    </nav>

    <footer class="home-footer">
      <span>Local research wiki</span>
      <span>Last compiled {html.escape(last_compiled)}</span>
    </footer>
  </main>
</body>
</html>
"""


def render_document_page(
    doc: dict[str, object],
    docs: list[dict[str, object]],
    root: Path,
    export_root: Path,
    title_to_export: dict[str, Path],
    source_to_export: dict[Path, Path],
) -> str:
    source_path = Path(doc["source_path"])
    export_path = Path(doc["export_path"])
    if export_path == Path("index.html"):
        return render_index_page(doc, docs, root, export_root, title_to_export, source_to_export)
    text = read_text(source_path)
    body_html = render_markdown_blocks(strip_frontmatter(text), source_path, export_path, root, export_root, title_to_export, source_to_export)
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    breadcrumb = source_path.relative_to(root).as_posix()
    title = str(doc["title"])
    # Keep original heading anchors and all content, while presenting the title once.
    first_heading = re.search(r'<h1 id="([^"]*)">.*?</h1>', body_html, re.S)
    title_id = first_heading.group(1) if first_heading else "document-title"
    body_html = re.sub(r'<h1 id="[^"]*">.*?</h1>', "", body_html, count=1, flags=re.S)
    toc = []
    for anchor, heading in re.findall(r'<h2 id="([^"]*)">(.*?)</h2>', body_html, re.S):
        label = html.unescape(re.sub(r'<[^>]+>', '', heading))
        toc.append(f'<a href="#{html.escape(anchor, quote=True)}">{html.escape(label)}</a>')
    body_html = body_html.replace('<table>', '<div class="table-scroll" role="region" aria-label="Research data table" tabindex="0"><table>').replace('</table>', '</table></div>')
    is_project = doc.get("note_type") == "project"
    category = "Subproject" if doc.get("parent_project_id") else "Research project" if is_project else str(doc["group"]).removesuffix("s")
    status = str(doc.get("project_status") or "")
    updated = str(doc.get("snapshot_date") or doc.get("last_compiled") or doc.get("year") or "")
    status_html = f'<span class="status-pill" data-status="{html.escape(status, quote=True)}">{html.escape(status.title())}</span>' if status else ""
    date_html = f'<span>Updated {html.escape(updated)}</span>' if updated else ""
    parent = next((item for item in docs if item.get("project_id") and item.get("project_id") == doc.get("parent_project_id")), None)
    parent_html = ""
    if parent:
        parent_href = relative_href(Path(parent["export_path"]), export_path)
        parent_html = f'<a href="{html.escape(parent_href, quote=True)}">Part of {html.escape(str(parent.get("project_name") or parent["title"]))}</a>'
    script_href = relative_href(Path("assets/wiki-ui.js"), export_path)
    compact_title = str(doc.get("project_name") or title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · Research Wiki</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
  <script src="{html.escape(script_href, quote=True)}" defer></script>
</head>
<body class="workspace document-page">
  {render_workspace_shell(docs, export_path, compact_title)}
  <main class="document-main" id="main-content">
    <header class="document-header">
      <div class="document-eyebrow"><span>{html.escape(category)}</span>{status_html}</div>
      <h1 id="{html.escape(title_id, quote=True)}">{html.escape(title)}</h1>
      <div class="document-meta">{date_html}{parent_html}<span>{max(1, len(strip_frontmatter(text).split()) // 220)} min read</span></div>
    </header>
    <details class="mobile-toc"><summary>On this page</summary><nav aria-label="Page sections">{''.join(toc)}</nav></details>
    <div class="document-layout">
      <article class="content">
        {body_html}
        <footer class="document-footer">Source note <code>{html.escape(breadcrumb)}</code></footer>
      </article>
      <aside class="document-toc" aria-label="On this page"><p class="toc-label">On this page</p><nav class="toc-links">{''.join(toc)}</nav><a class="toc-top" href="#{html.escape(title_id, quote=True)}">Back to top ↑</a></aside>
    </div>
  </main>
</body>
</html>
"""


def render_search_page(docs: list[dict[str, object]], root: Path, search_index: dict[str, object]) -> str:
    del root
    export_path = Path("search.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    record_count = len(search_index.get("documents", []))
    search_data = json_for_html(search_index)
    script = """
const searchInput = document.querySelector('[data-search-input]');
const resultsEl = document.querySelector('[data-search-results]');
const statusEl = document.querySelector('[data-search-status]');
const searchDataEl = document.getElementById('search-index-data');

const escapeHtml = (value) =>
  value.replace(/[&<>\"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));

const params = new URLSearchParams(window.location.search);
const groupButtons = [...document.querySelectorAll('[data-search-group]')];
const moreButton = document.querySelector('[data-search-more]');
let selectedGroup = params.get('group') || '';
if (!groupButtons.some(button => button.dataset.searchGroup === selectedGroup)) selectedGroup = '';
let visibleCount = 30;
const records = JSON.parse(searchDataEl.textContent || '{"documents": []}').documents || [];

const tokenize = (query) =>
  query.toLowerCase().trim().split(/\\s+/).filter(Boolean);

const scoreRecord = (record, tokens) => {
  const title = record.title.toLowerCase();
  const aliases = (record.aliases || []).join(' ').toLowerCase();
  const meta = [record.group, record.note_type, record.project_id, record.project_level, record.parent_project_id, record.project_status, record.year, record.venue, record.doi, record.arxiv_id, ...(record.github_links || [])]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  let score = 0;
  let matched = 0;
  for (const token of tokens) {
    let tokenHit = false;
    if (title.includes(token)) {
      score += 12;
      tokenHit = true;
    }
    if (aliases.includes(token)) {
      score += 8;
      tokenHit = true;
    }
    if (meta.includes(token)) {
      score += 6;
      tokenHit = true;
    }
    const occurrences = record.search_text.split(token).length - 1;
    if (occurrences > 0) {
      score += Math.min(occurrences, 8);
      tokenHit = true;
    }
    if (tokenHit) {
      matched += 1;
    }
  }
  if (matched === tokens.length) {
    score += 15;
  }
  return score;
};

const renderCards = (query) => {
  const tokens = tokenize(query);
  groupButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.searchGroup === selectedGroup)));
  const matches = records
    .filter(record => !selectedGroup || record.group === selectedGroup)
    .map((record) => ({ record, score: tokens.length ? scoreRecord(record, tokens) : 1 }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || left.record.title.localeCompare(right.record.title));
  const ranked = matches.slice(0, visibleCount);
  moreButton.hidden = matches.length <= visibleCount;
  statusEl.textContent = `${matches.length} page${matches.length === 1 ? '' : 's'}${selectedGroup ? ` in ${selectedGroup.toLowerCase()}` : ' in your library'}${query ? ` matching “${query}”` : ''} · Showing ${ranked.length}`;
  if (!ranked.length) {
    resultsEl.innerHTML = '<div class="tool-empty">No matching pages yet. Try a concept name, author, GitHub repo, DOI, venue, or year.</div>';
    return;
  }
  resultsEl.innerHTML = ranked.map(({ record }) => {
    const pills = [
      record.group,
      record.project_status,
      record.year,
      record.venue
    ].filter(Boolean).map((value) => `<span class="pill">${escapeHtml(String(value))}</span>`).join('');
    const ids = [
      record.doi ? `<span class="pill">DOI ${escapeHtml(record.doi)}</span>` : '',
      record.arxiv_id ? `<span class="pill">arXiv ${escapeHtml(record.arxiv_id)}</span>` : '',
      (record.github_links || []).length ? `<span class="pill">GitHub</span>` : ''
    ].join('');
    return `
      <article class="tool-result">
        <h2><a href="${escapeHtml(record.href)}">${escapeHtml(record.title)}</a></h2>
        <div class="result-meta">${pills}${ids}</div>
        <p>${escapeHtml(record.summary || 'No summary yet.')}</p>
        <p class="result-path">${escapeHtml(record.path)}</p>
      </article>
    `;
  }).join('');
};

const updateSearch = () => {
  const query = searchInput.value.trim();
  const nextParams = new URLSearchParams(window.location.search);
  if (query) {
    nextParams.set('q', query);
  } else {
    nextParams.delete('q');
  }
  if (selectedGroup) nextParams.set('group', selectedGroup);
  else nextParams.delete('group');
  const nextUrl = `${window.location.pathname}${nextParams.toString() ? `?${nextParams.toString()}` : ''}`;
  try { window.history.replaceState({}, '', nextUrl); } catch (_) { /* Some file viewers disallow history updates. */ }
  renderCards(query);
};

const init = () => {
  const initialQuery = params.get('q') || '';
  searchInput.value = initialQuery;
  renderCards(initialQuery);
};

searchInput.addEventListener('input', () => { visibleCount = 30; updateSearch(); });
groupButtons.forEach(button => button.addEventListener('click', () => {
  selectedGroup = button.dataset.searchGroup;
  visibleCount = 30;
  updateSearch();
}));
moreButton.addEventListener('click', () => { visibleCount += 30; renderCards(searchInput.value.trim()); });
window.addEventListener('keydown', (event) => {
  if (event.key === '/' && !event.target.closest('input,textarea,select,[contenteditable="true"]') && !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault();
    searchInput.focus();
  }
});

init();
""".strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <script src="assets/wiki-ui.js" defer></script>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Search The Wiki · Research Wiki</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body class="workspace tool-page">
  {render_workspace_shell(docs, export_path, "Search library")}

  <main class="tool-main" id="main-content">
    <section class="tool-intro">
      <div>
        <p class="tool-kicker">Library search</p>
        <h1>Find your next connection<span class="title-dot">.</span></h1>
        <p class="tool-lede">Find source pages, concepts, authors, venues, identifiers, and compiled summaries.</p>
      </div>
      <p class="tool-meta">{record_count} pages indexed</p>
    </section>

    <section class="search-workspace" aria-label="Wiki search">
      <div class="tool-search-box">
        {icon("search")}<input type="search" data-search-input aria-label="Search the research wiki" placeholder="Search papers, concepts, authors, DOI, arXiv...">
      </div>
      <div class="search-filters" role="group" aria-label="Filter library">
        <button type="button" data-search-group="" aria-pressed="true">All pages</button>
        <button type="button" data-search-group="Sources" aria-pressed="false">Sources</button>
        <button type="button" data-search-group="Concepts" aria-pressed="false">Concepts</button>
        <button type="button" data-search-group="Projects" aria-pressed="false">Projects</button>
        <button type="button" data-search-group="Derived" aria-pressed="false">Research notes</button>
        <button type="button" data-search-group="System" aria-pressed="false">System</button>
      </div>
      <div class="tool-search-status" data-search-status aria-live="polite">Loading search index...</div>
      <section class="tool-search-results" data-search-results></section>
      <button type="button" class="search-more" data-search-more hidden>Show more pages</button>
    </section>

    <footer class="home-footer">
      <span>Local research wiki</span>
      <a href="index.html">Back to overview</a>
    </footer>
  </main>
  <script id="search-index-data" type="application/json">{search_data}</script>
  <script>{script}</script>
</body>
</html>
"""


def render_knowledge_page(
    docs: list[dict[str, object]],
    root: Path,
    okf_result: dict[str, object],
) -> str:
    export_path = Path("knowledge.html")
    native_to_html = {
        Path(doc["source_path"]).relative_to(root).as_posix(): Path(doc["export_path"]).as_posix()
        for doc in docs
    }
    manifest = dict(okf_result["manifest"])
    graph_documents = []
    for item in manifest["documents"]:
        record = dict(item)
        record["html_href"] = native_to_html.get(str(record.get("native_path") or ""), "")
        record["collection"] = str(record["id"]).split("/", 1)[0]
        graph_documents.append(record)
    graph = {
        "documents": graph_documents,
        "relationships": manifest["relationships"],
    }
    graph_data = json_for_html(graph)
    summary = manifest["summary"]
    conformance = okf_result["conformance"]
    reviewed = int(summary["trust"]["human_reviewed"]) + int(summary["trust"]["machine_confirmed"])
    generated_at = str(manifest["generated_at"])
    status_label = "Valid OKF v0.2" if conformance["valid"] else "Conformance issues"
    script = r"""
const data = JSON.parse(document.getElementById('knowledge-data').textContent || '{"documents":[],"relationships":[]}');
const canvas = document.querySelector('[data-knowledge-canvas]');
const shell = canvas.parentElement;
const ctx = canvas.getContext('2d');
const searchInput = document.querySelector('[data-knowledge-search]');
const filterButtons = [...document.querySelectorAll('[data-knowledge-filter]')];
const inspector = {
  title: document.querySelector('[data-node-title]'),
  type: document.querySelector('[data-node-type]'),
  description: document.querySelector('[data-node-description]'),
  status: document.querySelector('[data-node-status]'),
  trust: document.querySelector('[data-node-trust]'),
  provenance: document.querySelector('[data-node-provenance]'),
  links: document.querySelector('[data-node-links]'),
  updated: document.querySelector('[data-node-updated]'),
  open: document.querySelector('[data-node-open]')
};

const palette = {
  projects: '#b4473a',
  concepts: '#287a5b',
  sources: '#3972b7',
  derived: '#8060a8',
  system: '#8a6b2f'
};
const labels = {
  projects: 'Projects',
  concepts: 'Concepts',
  sources: 'Sources',
  derived: 'Derived',
  system: 'System'
};
const zones = {
  projects: [0.04, 0.09, 0.25, 0.33],
  system: [0.04, 0.39, 0.25, 0.55],
  derived: [0.04, 0.64, 0.25, 0.88],
  concepts: [0.31, 0.09, 0.52, 0.91],
  sources: [0.59, 0.06, 0.96, 0.94]
};
const nodeById = new Map(data.documents.map((node) => [node.id, node]));
const adjacency = new Map(data.documents.map((node) => [node.id, new Set()]));
for (const edge of data.relationships) {
  if (!adjacency.has(edge.source) || !adjacency.has(edge.target)) continue;
  adjacency.get(edge.source).add(edge.target);
  adjacency.get(edge.target).add(edge.source);
}

let activeFilter = 'all';
let query = '';
let selected = data.documents.find((node) => node.id === 'projects/pfm') || data.documents.find((node) => node.collection === 'projects') || data.documents[0] || null;
let hovered = null;
let visibleNodes = [];
let width = 0;
let height = 0;

const titleCase = (value) => value ? value.replace(/[-_]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not recorded';
const matchesQuery = (node) => {
  if (!query) return true;
  const haystack = `${node.title} ${node.description} ${node.type} ${node.native_path}`.toLowerCase();
  return query.split(/\s+/).every((term) => haystack.includes(term));
};

const layoutGroup = (nodes, zone) => {
  if (!nodes.length) return;
  const [x1, y1, x2, y2] = zone;
  const zoneWidth = Math.max((x2 - x1) * width, 1);
  const zoneHeight = Math.max((y2 - y1) * height, 1);
  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length * zoneWidth / zoneHeight)));
  const rows = Math.max(1, Math.ceil(nodes.length / columns));
  nodes.forEach((node, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    node._x = x1 * width + ((column + 0.5) / columns) * zoneWidth;
    node._y = y1 * height + ((row + 0.5) / rows) * zoneHeight;
  });
};

const calculateLayout = () => {
  visibleNodes = data.documents.filter((node) => activeFilter === 'all' || node.collection === activeFilter);
  if (activeFilter === 'all') {
    Object.keys(zones).forEach((group) => {
      const members = visibleNodes
        .filter((node) => node.collection === group)
        .sort((a, b) => a.title.localeCompare(b.title));
      layoutGroup(members, zones[group]);
    });
  } else {
    layoutGroup([...visibleNodes].sort((a, b) => a.title.localeCompare(b.title)), [0.06, 0.1, 0.94, 0.9]);
  }
};

const nodeRadius = (node) => {
  if (node.collection === 'projects') return 6;
  if (node.collection === 'derived') return 4.8;
  if (node.collection === 'concepts') return 4;
  if (node.collection === 'system') return 4.5;
  return 2.4;
};

const draw = () => {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#fafcfb';
  ctx.fillRect(0, 0, width, height);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const matchedIds = new Set(visibleNodes.filter(matchesQuery).map((node) => node.id));
  const focusId = (hovered || selected || {}).id;

  if (activeFilter === 'all') {
    ctx.font = '700 10px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textBaseline = 'top';
    for (const [group, zone] of Object.entries(zones)) {
      ctx.fillStyle = '#87918c';
      ctx.fillText(labels[group].toUpperCase(), zone[0] * width, Math.max(10, zone[1] * height - 22));
    }
  }

  ctx.lineWidth = 0.7;
  for (const edge of data.relationships) {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    const focused = focusId && (edge.source === focusId || edge.target === focusId);
    if (query && !matchedIds.has(edge.source) && !matchedIds.has(edge.target) && !focused) continue;
    ctx.beginPath();
    ctx.moveTo(source._x, source._y);
    ctx.lineTo(target._x, target._y);
    ctx.strokeStyle = focused ? 'rgba(30, 74, 58, 0.52)' : edge.kind === 'source' ? 'rgba(57, 114, 183, 0.075)' : 'rgba(46, 75, 62, 0.045)';
    ctx.lineWidth = focused ? 1.4 : 0.65;
    ctx.stroke();
  }

  for (const node of visibleNodes) {
    const matched = matchesQuery(node);
    const isSelected = selected && selected.id === node.id;
    const isHovered = hovered && hovered.id === node.id;
    const radius = nodeRadius(node) + (isSelected || isHovered ? 2.2 : 0);
    ctx.beginPath();
    ctx.arc(node._x, node._y, radius, 0, Math.PI * 2);
    ctx.fillStyle = palette[node.collection] || '#66736d';
    ctx.globalAlpha = query && !matched && !isSelected ? 0.12 : 0.88;
    ctx.fill();
    ctx.globalAlpha = 1;
    if (isSelected || isHovered) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#17201c';
      ctx.stroke();
    }
  }
};

const resize = () => {
  const bounds = shell.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  width = Math.max(320, bounds.width);
  height = Math.max(360, canvas.getBoundingClientRect().height);
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  calculateLayout();
  draw();
};

const renderInspector = (node) => {
  if (!node) return;
  const connections = adjacency.get(node.id) || new Set();
  inspector.title.textContent = node.title;
  inspector.type.textContent = node.type;
  inspector.description.textContent = node.description || 'No description recorded.';
  inspector.status.textContent = titleCase(node.status);
  inspector.trust.textContent = titleCase(node.trust_tier);
  inspector.provenance.textContent = String(node.provenance_sources || 0);
  inspector.links.textContent = String(connections.size);
  inspector.updated.textContent = (node.generated_at || '').slice(0, 10) || 'Not recorded';
  if (node.html_href) {
    inspector.open.href = node.html_href;
    inspector.open.hidden = false;
  } else {
    inspector.open.hidden = true;
  }
};

const pointerNode = (event) => {
  const bounds = canvas.getBoundingClientRect();
  const x = event.clientX - bounds.left;
  const y = event.clientY - bounds.top;
  let nearest = null;
  let distance = 11;
  for (const node of visibleNodes) {
    const current = Math.hypot(node._x - x, node._y - y);
    if (current < distance) {
      distance = current;
      nearest = node;
    }
  }
  return nearest;
};

canvas.addEventListener('mousemove', (event) => {
  const next = pointerNode(event);
  if ((next || {}).id === (hovered || {}).id) return;
  hovered = next;
  canvas.style.cursor = hovered ? 'pointer' : 'default';
  draw();
});
canvas.addEventListener('mouseleave', () => {
  hovered = null;
  canvas.style.cursor = 'default';
  draw();
});
canvas.addEventListener('click', (event) => {
  const next = pointerNode(event);
  if (!next) return;
  selected = next;
  renderInspector(selected);
  draw();
});

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    activeFilter = button.dataset.knowledgeFilter;
    filterButtons.forEach((candidate) => candidate.setAttribute('aria-pressed', String(candidate === button)));
    if (selected && activeFilter !== 'all' && selected.collection !== activeFilter) {
      selected = data.documents.find((node) => node.collection === activeFilter) || selected;
      renderInspector(selected);
    }
    calculateLayout();
    draw();
  });
});
searchInput.addEventListener('input', () => {
  query = searchInput.value.trim().toLowerCase();
  const firstMatch = visibleNodes.find(matchesQuery);
  if (query && firstMatch) {
    selected = firstMatch;
    renderInspector(selected);
  }
  draw();
});

renderInspector(selected);
new ResizeObserver(resize).observe(shell);
resize();
""".strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <script src="assets/wiki-ui.js" defer></script>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Knowledge Map · Research Wiki</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="assets/wiki.css">
</head>
<body class="workspace tool-page knowledge-page">
  {render_workspace_shell(docs, export_path, "Knowledge map")}

  <main class="tool-main" id="main-content">
    <section class="tool-intro">
      <div>
        <p class="tool-kicker">Open Knowledge Format · v0.2</p>
        <h1>Knowledge Map</h1>
        <p class="tool-lede">Projects, concepts, source evidence, and derived work as one portable knowledge graph.</p>
      </div>
      <div class="knowledge-actions">
        <a href="assets/research-wiki-okf.zip" download>Download bundle</a>
        <a href="assets/okf-manifest.json">Manifest</a>
        <a href="assets/okf-conformance.json">Conformance</a>
      </div>
    </section>

    <dl class="knowledge-stats">
      <div><dt>Documents</dt><dd>{int(summary['documents']):,}</dd></div>
      <div><dt>Relationships</dt><dd>{int(summary['relationships']):,}</dd></div>
      <div><dt>Provenance records</dt><dd>{int(summary['provenance_sources']):,}</dd></div>
      <div><dt>Explicit reviews</dt><dd>{reviewed:,}</dd></div>
    </dl>

    <section class="knowledge-controls" aria-label="Knowledge graph controls">
      <div class="knowledge-filter" role="group" aria-label="Document collection">
        <button type="button" data-knowledge-filter="all" aria-pressed="true">All</button>
        <button type="button" data-knowledge-filter="projects" aria-pressed="false">Projects</button>
        <button type="button" data-knowledge-filter="concepts" aria-pressed="false">Concepts</button>
        <button type="button" data-knowledge-filter="sources" aria-pressed="false">Sources</button>
        <button type="button" data-knowledge-filter="derived" aria-pressed="false">Derived</button>
        <button type="button" data-knowledge-filter="system" aria-pressed="false">System</button>
      </div>
      <input class="knowledge-search" type="search" data-knowledge-search aria-label="Find a node" placeholder="Find a project, concept, or paper">
    </section>

    <section class="knowledge-workspace">
      <div class="knowledge-canvas-shell">
        <canvas data-knowledge-canvas aria-label="Research knowledge graph"></canvas>
        <ul class="knowledge-legend" aria-label="Graph legend">
          <li><span class="knowledge-dot" style="--dot:#b4473a"></span>Projects</li>
          <li><span class="knowledge-dot" style="--dot:#287a5b"></span>Concepts</li>
          <li><span class="knowledge-dot" style="--dot:#3972b7"></span>Sources</li>
          <li><span class="knowledge-dot" style="--dot:#8060a8"></span>Derived</li>
          <li><span class="knowledge-dot" style="--dot:#8a6b2f"></span>System</li>
        </ul>
      </div>
      <aside class="knowledge-inspector" aria-live="polite">
        <p class="knowledge-inspector-label">Selected document</p>
        <h2 data-node-title>Knowledge document</h2>
        <p class="knowledge-inspector-type" data-node-type></p>
        <p class="knowledge-inspector-description" data-node-description></p>
        <dl>
          <div><dt>Lifecycle</dt><dd data-node-status></dd></div>
          <div><dt>Trust tier</dt><dd data-node-trust></dd></div>
          <div><dt>Provenance</dt><dd data-node-provenance></dd></div>
          <div><dt>Connections</dt><dd data-node-links></dd></div>
          <div><dt>Updated</dt><dd data-node-updated></dd></div>
        </dl>
        <a class="knowledge-open" data-node-open href="#">Open document</a>
      </aside>
    </section>

    <p class="knowledge-note">
      <span><strong>{html.escape(status_label)}</strong> · {int(conformance['documents_checked']):,} Markdown files checked · {int(summary['stale_documents']):,} explicitly stale</span>
      <span>Trust reflects recorded verification events, not inferred review.</span>
    </p>

    <footer class="home-footer">
      <span>Generated {html.escape(generated_at)}</span>
      <a href="index.html">Back to overview</a>
    </footer>
  </main>
  <script id="knowledge-data" type="application/json">{graph_data}</script>
  <script>{script}</script>
</body>
</html>
"""


def ask_widget_script(server_command: str, local_server_url: str) -> str:
    return f"""
const formEl = document.querySelector('[data-ask-form]');
const textareaEl = document.querySelector('[data-ask-input]');
const submitEl = document.querySelector('[data-ask-submit]');
const statusEl = document.querySelector('[data-ask-status]');
const resultEl = document.querySelector('[data-ask-result]');
const metaEl = document.querySelector('[data-ask-meta]');
const serverNoteEl = document.querySelector('[data-server-note]');
const providerEl = document.querySelector('[data-provider-status]');
const fileIntoWikiEl = document.querySelector('[data-file-into-wiki]');
const emptyAnswerEl = document.querySelector('[data-answer-empty]');
const localServerUrl = {json.dumps(local_server_url)};
const apiBase = window.location.protocol === 'file:' ? 'http://127.0.0.1:8765' : '';
const queryToken = new URLSearchParams(window.location.search).get('wiki_token') || '';
if (queryToken) {{
  window.sessionStorage.setItem('research-wiki-token', queryToken);
}}
const wikiToken = queryToken || window.sessionStorage.getItem('research-wiki-token') || '';
const apiHeaders = wikiToken ? {{ 'X-Wiki-Token': wikiToken }} : {{}};
let timerId = null;
let requestStartedAt = 0;

const redirectFilePageToServer = async () => {{
  if (window.location.protocol !== 'file:') {{
    return false;
  }}
  try {{
    await fetch(localServerUrl, {{ method: 'GET', mode: 'no-cors', cache: 'no-store' }});
    window.location.replace(localServerUrl);
    return true;
  }} catch (error) {{
    return false;
  }}
}};

const escapeHtml = (value) =>
  value.replace(/[&<>\"']/g, (char) => ({{
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }}[char]));

const renderMeta = (payload) => {{
  const lines = [
    payload.provider ? `Provider: <code>${{escapeHtml(payload.provider)}}</code>` : '',
    payload.output ? `Output: <code>${{escapeHtml(payload.output)}}</code>` : '',
    payload.filed_into_wiki ? `Filed into wiki: <code>${{escapeHtml(payload.filed_into_wiki)}}</code>` : '',
    payload.context_mode ? `Context mode: <code>${{escapeHtml(payload.context_mode)}}</code>` : '',
    Array.isArray(payload.context_files) && payload.context_files.length
      ? `Context files: ${{payload.context_files.slice(0, 8).map((item) => `<code>${{escapeHtml(item)}}</code>`).join(' ')}}`
      : ''
  ].filter(Boolean);
  metaEl.innerHTML = lines.length ? '<details><summary>Sources &amp; saved answer</summary><div>' + lines.join('<br>') + '</div></details>' : '';
}};

const setUnavailable = () => {{
  providerEl.textContent = 'Subscription unavailable';
  providerEl.classList.remove('connected');
  providerEl.classList.add('unavailable');
  serverNoteEl.hidden = false;
  if (window.location.protocol === 'file:') {{
    serverNoteEl.innerHTML = `This static page can ask the wiki through the local server, but the server is not reachable right now. Open <a href="${{localServerUrl}}"><code>${{localServerUrl}}</code></a> after starting <code>{server_command}</code>.`;
    statusEl.textContent = 'Start the local server to use Q&A.';
  }} else {{
    serverNoteEl.innerHTML = `Local Q&A server is unavailable. Run <code>{server_command}</code> and reload this page.`;
    statusEl.textContent = 'Q&A server unavailable.';
  }}
  resultEl.textContent = 'The local Q&A server is currently unavailable.';
  emptyAnswerEl.hidden = true;
  metaEl.innerHTML = '';
  submitEl.disabled = true;
}};

const setLoading = () => {{
  requestStartedAt = Date.now();
  const render = () => {{
    const seconds = Math.max(1, Math.round((Date.now() - requestStartedAt) / 1000));
    statusEl.textContent = `Asking the wiki... ${{seconds}}s elapsed. Typical latency is 10-30s.`;
  }};
  render();
  timerId = window.setInterval(render, 1000);
}};

const clearLoading = () => {{
  if (timerId !== null) {{
    window.clearInterval(timerId);
    timerId = null;
  }}
}};

const checkServer = async () => {{
  if (await redirectFilePageToServer()) {{
    return;
  }}
  try {{
    const response = await fetch(`${{apiBase}}/api/health`, {{ method: 'GET', headers: apiHeaders }});
    if (!response.ok) {{
      throw new Error('Health check failed.');
    }}
    const payload = await response.json();
    providerEl.textContent = payload.provider === 'codex-subscription'
      ? 'GPT subscription connected'
      : (payload.provider || 'Q&A connected');
    providerEl.classList.remove('unavailable');
    providerEl.classList.add('connected');
    submitEl.disabled = false;
    serverNoteEl.hidden = true;
    serverNoteEl.innerHTML = '';
    statusEl.textContent = 'Ready when you are';
    resultEl.textContent = '';
    emptyAnswerEl.hidden = false;
  }} catch (error) {{
    setUnavailable();
  }}
}};

formEl.addEventListener('submit', async (event) => {{
  event.preventDefault();
  const question = textareaEl.value.trim();
  if (!question) {{
    statusEl.textContent = 'Enter a question first.';
    return;
  }}
  submitEl.disabled = true;
  formEl.setAttribute('aria-busy', 'true');
  emptyAnswerEl.hidden = true;
  setLoading();
  resultEl.textContent = '';
  metaEl.innerHTML = '';
  try {{
    const response = await fetch(`${{apiBase}}/api/ask`, {{
      method: 'POST',
      headers: {{ ...apiHeaders, 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        question,
        file_into_wiki: Boolean(fileIntoWikiEl && fileIntoWikiEl.checked)
      }})
    }});
    const payload = await response.json();
    if (!response.ok) {{
      throw new Error(payload.error || 'Q&A request failed.');
    }}
    statusEl.textContent = 'Answer ready.';
    if (window.WikiUI) {{
      window.WikiUI.renderAnswer(resultEl, payload.answer || 'No answer was returned. Try rephrasing your question.');
    }} else {{
      resultEl.textContent = payload.answer || '';
    }}
    renderMeta(payload);
  }} catch (error) {{
    console.error(error);
    statusEl.textContent = error.message || 'Q&A request failed.';
    resultEl.textContent = '';
    metaEl.innerHTML = '';
  }} finally {{
    clearLoading();
    formEl.removeAttribute('aria-busy');
    submitEl.disabled = false;
  }}
}});

submitEl.disabled = true;
checkServer();
""".strip()


def ask_widget_markup(*, compact: bool, show_file_into_wiki: bool, placeholder: str) -> str:
    form_class = "ask-form compact-ask" if compact else "ask-form"
    answer_class = "answer-shell compact-ask" if compact else "answer-shell"
    checkbox_html = ""
    if show_file_into_wiki:
        checkbox_html = """
                <label class="checkbox-row">
                  <input data-file-into-wiki type="checkbox" checked>
                  <span>Save answer to research notes</span>
                </label>"""
    return f"""
        <div class="ask-workspace">
          <section class="ask-question-pane">
            <h2>{icon("ask")} Your question</h2>
            <div class="{form_class}">
            <form data-ask-form>
              <label class="tool-label" for="wiki-question">Question</label>
              <textarea id="wiki-question" data-ask-input rows="7" placeholder="{html.escape(placeholder, quote=True)}" required></textarea>
              <div class="ask-actions">
                <button class="primary-button" data-ask-submit type="submit">Ask the Wiki {icon("arrow")}</button>{checkbox_html}
              </div>
            </form>
            </div>
            <div class="ask-suggestions">
              <p>A few starting points</p>
              <button type="button" data-question="What are the current milestones and open gaps across my active projects?">Where do my projects stand? {icon("arrow")}</button>
              <button type="button" data-question="How do the subprojects of my largest research programme fit together?">Connect the subprojects {icon("arrow")}</button>
              <button type="button" data-question="Compare neural operators and graph neural networks for learning physical simulations, using sources in the wiki.">Compare approaches to physics learning {icon("arrow")}</button>
            </div>
            <div class="server-note" data-server-note hidden></div>
          </section>
          <section class="ask-answer-pane {answer_class}">
            <div class="ask-answer-heading">
              <h2>Research answer</h2>
              <span class="ask-status" data-ask-status aria-live="polite">Ready when you are</span>
            </div>
            <div class="answer-empty" data-answer-empty>{icon("sources")}<h3>Start with a good question.</h3><p>Explore ideas across your projects and papers.<br>Your answer and source context will appear here.</p></div>
            <div class="answer-output" data-ask-result></div>
            <div class="answer-meta" data-ask-meta></div>
          </section>
        </div>""".rstrip()


def render_ask_page(docs: list[dict[str, object]], root: Path) -> str:
    del root
    export_path = Path("ask.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    server_command = ".venv/bin/python _meta/scripts/wiki_cli.py serve-html --root ."
    local_server_url = "http://127.0.0.1:8765/ask.html"
    script = ask_widget_script(server_command, local_server_url)
    widget_html = ask_widget_markup(
        compact=False,
        show_file_into_wiki=True,
        placeholder="What would you like to explore? Ask about a project, compare methods, or follow an idea across your sources…",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <script src="assets/wiki-ui.js" defer></script>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ask The Wiki · Research Wiki</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body class="workspace tool-page ask-page">
  {render_workspace_shell(docs, export_path, "Ask the Wiki")}

  <main class="tool-main" id="main-content">
    <section class="tool-intro">
      <div>
        <p class="tool-kicker">A conversation with your research</p>
        <h1>Ask the Wiki<span class="title-dot">.</span></h1>
        <p class="tool-lede">From a question to a clearer picture, grounded in your library.</p>
      </div>
      <p class="tool-meta provider-status" data-provider-status>Checking subscription</p>
    </section>

    {widget_html}

    <footer class="home-footer">
      <span>Local research wiki</span>
      <a href="index.html">Back to overview</a>
    </footer>
  </main>
  <script>{script}</script>
</body>
</html>
"""


def export_html(root: Path) -> dict[str, object]:
    config = load_config(root)
    published_root = root / config.get("html_dir", "output/html")
    export_root = published_root.parent / f".{published_root.name}-build-{os.getpid()}"
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True, exist_ok=True)
    (export_root / "assets").mkdir(parents=True, exist_ok=True)
    (export_root / "assets" / "wiki.css").write_text(STYLE_CSS + "\n", encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("wiki_ui.js"), export_root / "assets" / "wiki-ui.js")

    okf_result = export_okf(root)
    shutil.copy2(root / str(okf_result["archive_path"]), export_root / "assets" / "research-wiki-okf.zip")
    shutil.copy2(root / str(okf_result["manifest_path"]), export_root / "assets" / "okf-manifest.json")
    shutil.copy2(root / str(okf_result["conformance_path"]), export_root / "assets" / "okf-conformance.json")

    docs, title_to_export, source_to_export = build_doc_index(root)
    search_index = build_search_index(root, docs)
    written = []
    for doc in docs:
        export_path = export_root / Path(doc["export_path"])
        export_path.parent.mkdir(parents=True, exist_ok=True)
        html_text = render_document_page(doc, docs, root, export_root, title_to_export, source_to_export)
        export_path.write_text(html_text, encoding="utf-8")
        written.append((published_root / export_path.relative_to(export_root)).relative_to(root).as_posix())

    search_index_path = export_root / "assets" / "search-index.json"
    search_index_path.write_text(json.dumps(search_index, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append((published_root / search_index_path.relative_to(export_root)).relative_to(root).as_posix())

    search_page_path = export_root / "search.html"
    search_page_path.write_text(render_search_page(docs, root, search_index), encoding="utf-8")
    written.append((published_root / search_page_path.relative_to(export_root)).relative_to(root).as_posix())

    ask_page_path = export_root / "ask.html"
    ask_page_path.write_text(render_ask_page(docs, root), encoding="utf-8")
    written.append((published_root / ask_page_path.relative_to(export_root)).relative_to(root).as_posix())

    knowledge_page_path = export_root / "knowledge.html"
    knowledge_page_path.write_text(render_knowledge_page(docs, root, okf_result), encoding="utf-8")
    written.append((published_root / knowledge_page_path.relative_to(export_root)).relative_to(root).as_posix())

    previous_root = published_root.parent / f".{published_root.name}-previous-{os.getpid()}"
    if previous_root.exists():
        shutil.rmtree(previous_root)
    if published_root.exists():
        published_root.rename(previous_root)
    export_root.rename(published_root)
    if previous_root.exists():
        shutil.rmtree(previous_root)

    return {
        "export_root": published_root.relative_to(root).as_posix(),
        "entrypoint": (published_root / "index.html").relative_to(root).as_posix(),
        "search_page": (published_root / "search.html").relative_to(root).as_posix(),
        "ask_page": (published_root / "ask.html").relative_to(root).as_posix(),
        "knowledge_page": (published_root / "knowledge.html").relative_to(root).as_posix(),
        "okf_bundle": okf_result["bundle_root"],
        "okf_archive": okf_result["archive_path"],
        "okf_conformant": okf_result["conformance"]["valid"],
        "pages_written": len(written),
        "written": written,
    }


def export_html_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    result = export_html(parse_root_arg(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(export_html_main())
