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

from wiki_pipeline import detect_title, load_config, note_blurb, parse_root_arg, read_text, slugify, strip_frontmatter


EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:")

STYLE_CSS = """
:root {
  color-scheme: light;
  --bg: #eaecf0;
  --panel: #ffffff;
  --panel-soft: #f8f9fa;
  --text: #202122;
  --muted: #54595d;
  --accent: #3366cc;
  --accent-soft: #eef3ff;
  --border: #c8ccd1;
  --code-bg: #f8f9fa;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code, pre {
  font-family: "SFMono-Regular", "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}
.layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow: auto;
  padding: 28px 22px 36px;
  border-right: 1px solid var(--border);
  background: var(--panel-soft);
}
.brand {
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border);
}
.brand h1 {
  margin: 0;
  font-size: 1.4rem;
  line-height: 1.2;
  font-family: "Linux Libertine", "Georgia", serif;
}
.brand p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}
.nav-group {
  margin-top: 18px;
}
.nav-group h2 {
  margin: 0 0 8px;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.nav-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.nav-group li {
  margin: 0;
}
.nav-group a {
  display: block;
  padding: 6px 8px;
  border-radius: 8px;
  color: var(--text);
}
.nav-group a.current {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.content-shell {
  padding: 38px 48px 56px;
}
.content {
  max-width: 980px;
  margin: 0 auto;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 2px;
  box-shadow: var(--shadow);
  padding: 42px 48px 54px;
}
.breadcrumb {
  margin-bottom: 14px;
  color: var(--muted);
  font-size: 0.92rem;
}
.breadcrumb span {
  color: var(--muted);
}
h1, h2, h3, h4 {
  line-height: 1.2;
  scroll-margin-top: 24px;
  font-family: "Linux Libertine", "Georgia", serif;
}
h1 { font-size: 2.2rem; margin-top: 0; margin-bottom: 1rem; }
h2 {
  margin-top: 2.2rem;
  padding-top: 0.35rem;
  border-top: 1px solid var(--border);
  font-size: 1.45rem;
}
h3 { margin-top: 1.6rem; font-size: 1.18rem; }
p, ul, ol, blockquote, pre, table { margin: 1rem 0; }
blockquote {
  margin-left: 0;
  padding: 0.85rem 1rem;
  border-left: 3px solid var(--border);
  background: var(--panel-soft);
}
pre {
  overflow: auto;
  padding: 1rem;
  border-radius: 2px;
  background: var(--code-bg);
  border: 1px solid var(--border);
}
code {
  background: var(--code-bg);
  padding: 0.12rem 0.35rem;
  border-radius: 6px;
}
pre code {
  background: transparent;
  padding: 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border: 1px solid var(--border);
}
th, td {
  padding: 0.72rem 0.8rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  text-align: left;
}
thead th {
  background: var(--panel-soft);
}
tbody tr:nth-child(even) td {
  background: rgba(240, 232, 220, 0.35);
}
hr {
  border: 0;
  border-top: 1px solid var(--border);
  margin: 2rem 0;
}
img {
  max-width: 100%;
  height: auto;
  border-radius: 14px;
  border: 1px solid var(--border);
  box-shadow: 0 12px 26px rgba(78, 55, 34, 0.08);
}
.footer {
  margin-top: 2.5rem;
  color: var(--muted);
  font-size: 0.92rem;
}
.search-link {
  display: block;
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 2px;
  border: 1px solid var(--accent);
  background: var(--panel);
  color: var(--accent);
  font-weight: 600;
  text-align: center;
}
.search-link:hover {
  text-decoration: none;
  background: var(--accent-soft);
}
.search-link.current {
  background: var(--accent);
  color: #fff;
}
.sidebar-actions {
  display: grid;
  gap: 10px;
}
.sidebar-summary {
  margin-top: 14px;
  padding: 0 0 14px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.5;
}
.sidebar-summary strong {
  color: var(--text);
  font-weight: 600;
}
.sidebar-actions.compact-actions {
  margin-top: 16px;
}
.search-hero {
  margin-bottom: 1.6rem;
}
.search-hero p {
  color: var(--muted);
  max-width: 58ch;
}
.search-box {
  display: flex;
  gap: 12px;
  align-items: center;
  margin: 1.2rem 0 1.4rem;
}
.search-box input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #fff;
  font: inherit;
}
.search-hint {
  color: var(--muted);
  font-size: 0.92rem;
}
.search-results {
  display: grid;
  gap: 14px;
  margin-top: 1.5rem;
}
.result-card {
  padding: 18px 18px 16px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: var(--panel);
}
.result-card h2 {
  margin: 0;
  padding: 0;
  border: 0;
  font-size: 1.18rem;
}
.result-card p {
  margin: 0.55rem 0 0;
}
.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0.85rem 0;
}
.pill {
  display: inline-flex;
  padding: 0.26rem 0.58rem;
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--muted);
  font-size: 0.82rem;
}
.result-path {
  color: var(--muted);
  font-size: 0.88rem;
}
.empty-state {
  padding: 22px;
  border: 1px dashed var(--border);
  border-radius: 2px;
  background: var(--panel);
  color: var(--muted);
}
.ask-layout {
  display: grid;
  gap: 18px;
}
.ask-form {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: var(--panel);
}
.ask-form textarea {
  width: 100%;
  min-height: 140px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: #fff;
  font: inherit;
  resize: vertical;
}
.ask-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
}
.primary-button {
  border: 0;
  border-radius: 2px;
  background: var(--accent);
  color: #fff;
  font: inherit;
  font-weight: 600;
  padding: 11px 16px;
  cursor: pointer;
}
.primary-button:hover {
  filter: brightness(1.05);
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: wait;
}
.checkbox-row {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  color: var(--muted);
  font-size: 0.94rem;
}
.server-note {
  padding: 18px;
  border: 1px dashed var(--border);
  border-radius: 2px;
  background: var(--panel);
  color: var(--muted);
}
.answer-shell {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: var(--panel);
}
.answer-output {
  white-space: pre-wrap;
  font-family: "SFMono-Regular", "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.94rem;
  line-height: 1.6;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 16px;
  overflow-x: auto;
}
.answer-meta {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}
.answer-meta code {
  background: var(--code-bg);
  padding: 0.12rem 0.35rem;
  border-radius: 8px;
}
.index-shell {
  padding-top: 28px;
}
.index-content {
  max-width: 1160px;
}
.section-kicker {
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: inherit;
}
.lead-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) 320px;
  gap: 28px;
  align-items: start;
}
.lead-copy h1 {
  margin-bottom: 0.75rem;
}
.lead-text {
  font-size: 1.08rem;
}
.overview-note {
  color: var(--muted);
  max-width: 68ch;
}
.home-infobox {
  border: 1px solid var(--border);
  background: var(--panel-soft);
  padding: 16px;
}
.home-infobox h2 {
  margin: 0 0 12px;
  padding: 0;
  border: 0;
  font-size: 1.2rem;
}
.home-infobox table {
  margin: 0;
  background: var(--panel);
  table-layout: fixed;
}
.home-infobox th,
.home-infobox td,
.home-infobox code {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.toc-box {
  margin-top: 22px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  background: var(--panel-soft);
}
.toc-box h2 {
  margin: 0 0 12px;
  padding: 0;
  border: 0;
}
.toc-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.toc-box ul {
  margin: 0;
  padding-left: 18px;
}
.portal-section {
  margin-top: 28px;
}
.portal-heading {
  margin-bottom: 14px;
}
.portal-heading h2 {
  margin-bottom: 0.35rem;
}
.portal-heading p {
  margin: 0;
  color: var(--muted);
}
.portal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.portal-box {
  padding: 16px 18px;
  border: 1px solid var(--border);
  background: var(--panel);
}
.portal-box h3 {
  margin: 0 0 0.55rem;
  border: 0;
  padding: 0;
  font-size: 1.18rem;
}
.portal-box p {
  margin: 0.55rem 0 0;
}
.box-count {
  color: var(--muted);
  font-size: 0.94rem;
}
.portal-list {
  margin: 0.8rem 0 0;
  padding-left: 18px;
}
.portal-list li {
  margin: 0.28rem 0;
}
.portal-list span {
  color: var(--muted);
  margin-left: 0.4rem;
  font-size: 0.88rem;
}
.meta-line {
  display: block;
  margin-top: 0.3rem;
  color: var(--muted);
  font-size: 0.9rem;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 0.85rem;
}
.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.22rem 0.52rem;
  border: 1px solid var(--border);
  background: var(--panel-soft);
  color: var(--accent);
  font-size: 0.84rem;
}
.tag:hover {
  text-decoration: none;
  background: var(--accent-soft);
}
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 24px;
  list-style: none;
  padding: 0;
}
.catalog-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.concept-group-block + .concept-group-block {
  margin-top: 16px;
}
.concept-group-block h3 {
  margin: 0 0 0.65rem;
  padding: 0;
  border: 0;
}
.compact-box p {
  color: var(--muted);
}
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .content-shell {
    padding: 20px 16px 28px;
  }
  .content {
    padding: 28px 20px 32px;
    border-radius: 2px;
  }
  .lead-layout,
  .portal-grid,
  .toc-columns,
  .catalog-grid {
    grid-template-columns: 1fr;
  }
}
""".strip()


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
            "concepts": parse_list_field(text, "concepts"),
            "related": parse_list_field(text, "related"),
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
                source_path.relative_to(root).as_posix(),
                compact_text(body, limit=6000),
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


def relative_href(target: Path, current_export_path: Path) -> str:
    return os.path.relpath(target, start=current_export_path.parent).replace(os.sep, "/")


def copy_asset(source_abs: Path, root: Path, export_root: Path) -> Path:
    try:
        rel = source_abs.relative_to(root)
    except ValueError:
        rel = Path(source_abs.name)
    destination = export_root / "_files" / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_abs, destination)
    return destination


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
        "derived": sum(1 for doc in docs if doc["group"] == "Derived"),
        "system": sum(1 for doc in docs if doc["group"] == "System"),
    }


def is_portal_page(export_path: Path) -> bool:
    return export_path in {Path("index.html"), Path("search.html"), Path("ask.html")}


def find_doc(docs: list[dict[str, object]], export_path: str) -> dict[str, object] | None:
    target = Path(export_path)
    return next((doc for doc in docs if Path(doc["export_path"]) == target), None)


def render_portal_sidebar(docs: list[dict[str, object]], current_export_path: Path) -> str:
    counts = collection_counts(docs)
    overview_doc = find_doc(docs, "SYSTEM_OVERVIEW.html")
    lint_doc = find_doc(docs, "LINT_AND_HEAL.html")
    dashboard_doc = find_doc(docs, "DASHBOARD.html")
    home_href = relative_href(Path("index.html"), current_export_path)
    search_href = relative_href(Path("search.html"), current_export_path)
    ask_href = relative_href(Path("ask.html"), current_export_path)
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
        f'<strong>{counts["derived"]}</strong> derived notes',
        "</div>",
        '<nav class="nav-group"><h2>Navigation</h2><ul>',
        f'<li><a class="{"current" if current_export_path == Path("index.html") else ""}" href="{html.escape(home_href, quote=True)}">Main Page</a></li>',
    ]
    if overview_doc:
        parts.append(
            f'<li><a href="{html.escape(relative_href(Path(overview_doc["export_path"]), current_export_path), quote=True)}">System Overview</a></li>'
        )
    parts.append("</ul></nav>")
    parts.extend(
        [
            '<nav class="nav-group"><h2>Tools</h2><ul>',
            f'<li><a class="{"current" if current_export_path == Path("search.html") else ""}" href="{html.escape(search_href, quote=True)}">Search The Wiki</a></li>',
            f'<li><a class="{"current" if current_export_path == Path("ask.html") else ""}" href="{html.escape(ask_href, quote=True)}">Ask The Wiki</a></li>',
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
    groups: dict[str, list[dict[str, object]]] = {"System": [], "Sources": [], "Concepts": [], "Derived": [], "Other": []}
    for doc in docs:
        groups[str(doc["group"])].append(doc)

    search_current = " current" if current_export_path == Path("search.html") else ""
    ask_current = " current" if current_export_path == Path("ask.html") else ""
    parts = [
        '<div class="brand">',
        "<h1>Research Wiki</h1>",
        "<p>User-facing HTML export of the compiled vault.</p>",
        "</div>",
        '<div class="sidebar-actions">',
        f'<a class="search-link{search_current}" href="{html.escape(relative_href(Path("search.html"), current_export_path), quote=True)}">Search The Wiki</a>',
        f'<a class="search-link{ask_current}" href="{html.escape(relative_href(Path("ask.html"), current_export_path), quote=True)}">Ask The Wiki</a>',
        "</div>",
    ]
    for group_name in ("System", "Sources", "Concepts", "Derived", "Other"):
        items = groups[group_name]
        if not items:
            continue
        parts.append(f'<nav class="nav-group"><h2>{html.escape(group_name)}</h2><ul>')
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
    del export_root, source_to_export
    export_path = Path("index.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    sidebar_html = render_sidebar(docs, export_path)
    source_docs = [item for item in docs if item["group"] == "Sources"]
    concept_docs = [item for item in docs if item["group"] == "Concepts"]
    system_docs = [item for item in docs if item["group"] == "System" and Path(item["export_path"]) != export_path]
    derived_docs = [item for item in docs if item["group"] == "Derived"]
    counts = collection_counts(docs)
    overview_doc = find_doc(docs, "SYSTEM_OVERVIEW.html")
    last_compiled = str(doc.get("last_compiled") or (overview_doc or {}).get("last_compiled") or "Unknown")
    overview_summary = (
        "Sources remain immutable in raw/, transcript artifacts and compiler state live in _meta/, "
        "the wiki compiler maintains linked source and concept pages in wiki/, and useful answers can be filed back into the vault as new knowledge."
    )

    featured_sources = sorted(
        source_docs,
        key=lambda item: (-coerce_int(item.get("year")), str(item["title"]).lower()),
    )[:6]
    source_library = sorted(
        source_docs,
        key=lambda item: (-coerce_int(item.get("year")), str(item["title"]).lower()),
    )
    grouped_concepts: dict[str, list[dict[str, object]]] = defaultdict(list)
    for concept_doc in concept_docs:
        grouped_concepts[str(concept_doc.get("concept_group") or "Other")].append(concept_doc)
    ordered_groups = sorted(grouped_concepts.items(), key=lambda item: item[0].lower())
    for _, items in ordered_groups:
        items.sort(key=lambda item: (-coerce_int(item.get("source_count")), str(item["title"]).lower()))
    top_concepts = sorted(
        concept_docs,
        key=lambda item: (-coerce_int(item.get("source_count")), str(item["title"]).lower()),
    )[:12]

    collection_boxes = [
        {
            "title": "Source Pages",
            "count": counts["sources"],
            "href": "#source-library",
            "body": "One article per source document, with citation metadata, abstract, key concepts, and provenance.",
        },
        {
            "title": "Concept Pages",
            "count": counts["concepts"],
            "href": "#concept-atlas",
            "body": "Cross-source synthesis pages that connect methods, domains, and recurring research themes.",
        },
        {
            "title": "Search",
            "count": None,
            "href": "search.html",
            "body": "Full-text search across titles, concepts, DOI, arXiv, venues, and compiled summaries.",
        },
        {
            "title": "Q&A",
            "count": None,
            "href": "ask.html",
            "body": "Ask the wiki a question and render answers as markdown, slides, or filed-back notes.",
        },
    ]

    collections_html = []
    for box in collection_boxes:
        count_html = f'<div class="box-count">{box["count"]}</div>' if box["count"] is not None else ""
        href = box["href"]
        collections_html.append(
            f"""<article class="portal-box">
  <h3><a href="{html.escape(href, quote=True)}">{html.escape(box["title"])}</a></h3>
  {count_html}
  <p>{html.escape(box["body"])}</p>
</article>"""
        )

    research_areas_html = []
    for group_name, items in ordered_groups:
        top_items = items[:4]
        links = []
        for item in top_items:
            href = relative_href(Path(item["export_path"]), export_path)
            links.append(
                f'<li><a href="{html.escape(href, quote=True)}">{html.escape(str(item["title"]))}</a> <span>{coerce_int(item.get("source_count"))}</span></li>'
            )
        research_areas_html.append(
            f"""<article class="portal-box">
  <h3>{html.escape(group_name)}</h3>
  <p>{len(items)} concept pages in this cluster.</p>
  <ul class="portal-list">{''.join(links)}</ul>
</article>"""
        )

    featured_sources_html = []
    for source_doc in featured_sources:
        href = relative_href(Path(source_doc["export_path"]), export_path)
        meta_parts = [value for value in [source_doc.get("year"), source_doc.get("lead_author"), source_doc.get("venue")] if value]
        meta_html = f'<p class="meta-line">{" • ".join(html.escape(str(part)) for part in meta_parts)}</p>' if meta_parts else ""
        tags_html = render_doc_tags(list(source_doc.get("concepts") or []), export_path, title_to_export)
        summary = summarize_text(str(source_doc.get("summary") or ""))
        featured_sources_html.append(
            f"""<article class="portal-box source-box">
  <h3><a href="{html.escape(href, quote=True)}">{html.escape(str(source_doc["title"]))}</a></h3>
  {meta_html}
  <p>{html.escape(summary)}</p>
  {tags_html}
</article>"""
        )

    source_library_html = []
    for source_doc in source_library:
        href = relative_href(Path(source_doc["export_path"]), export_path)
        meta_parts = [value for value in [source_doc.get("year"), source_doc.get("lead_author")] if value]
        if source_doc.get("venue"):
            meta_parts.append(source_doc["venue"])
        source_library_html.append(
            f"""<li class="catalog-item">
  <a href="{html.escape(href, quote=True)}">{html.escape(str(source_doc["title"]))}</a>
  <span class="meta-line">{" • ".join(html.escape(str(part)) for part in meta_parts if part)}</span>
</li>"""
        )

    concept_group_html = []
    for group_name, items in ordered_groups:
        tags = []
        for item in items[:8]:
            href = relative_href(Path(item["export_path"]), export_path)
            tags.append(
                f'<a class="tag" href="{html.escape(href, quote=True)}">{html.escape(str(item["title"]))}</a>'
            )
        concept_group_html.append(
            f"""<section class="concept-group-block">
  <h3>{html.escape(group_name)}</h3>
  <div class="tag-row">{''.join(tags)}</div>
</section>"""
        )

    system_html = []
    for system_doc in sorted(system_docs, key=lambda item: str(item["title"]).lower()):
        href = relative_href(Path(system_doc["export_path"]), export_path)
        summary = summarize_text(str(system_doc.get("summary") or ""), 160)
        system_html.append(
            f"""<article class="portal-box compact-box">
  <h3><a href="{html.escape(href, quote=True)}">{html.escape(str(system_doc["title"]))}</a></h3>
  <p>{html.escape(summary)}</p>
</article>"""
        )

    derived_html = []
    for derived_doc in sorted(derived_docs, key=lambda item: str(item["title"]).lower()):
        href = relative_href(Path(derived_doc["export_path"]), export_path)
        summary = summarize_text(str(derived_doc.get("summary") or ""), 140)
        derived_html.append(
            f"""<li class="catalog-item">
  <a href="{html.escape(href, quote=True)}">{html.escape(str(derived_doc["title"]))}</a>
  <span class="meta-line">{html.escape(summary)}</span>
</li>"""
        )

    top_concept_links = []
    for concept_doc in top_concepts:
        href = relative_href(Path(concept_doc["export_path"]), export_path)
        top_concept_links.append(
            f'<li><a href="{html.escape(href, quote=True)}">{html.escape(str(concept_doc["title"]))}</a> <span>{coerce_int(concept_doc.get("source_count"))}</span></li>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Wiki</title>
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      {sidebar_html}
    </aside>
    <div class="content-shell index-shell">
      <main class="content index-content">
        <div class="breadcrumb"><span>wiki/INDEX.md</span></div>
        <section class="lead-layout" id="overview">
          <div class="lead-copy">
            <div class="section-kicker">Compiled main page</div>
            <h1>Research Wiki</h1>
            <p class="lead-text">A living reference built from local research sources in <code>raw/</code>, compiled into linked source pages, concept pages, and derived outputs inside <code>wiki/</code>.</p>
            <p class="overview-note">{html.escape(overview_summary)}</p>
          </div>
          <aside class="home-infobox">
            <h2>At a glance</h2>
            <table>
              <tbody>
                <tr><th>Last compiled</th><td>{html.escape(last_compiled)}</td></tr>
                <tr><th>Source pages</th><td>{counts["sources"]}</td></tr>
                <tr><th>Concept pages</th><td>{counts["concepts"]}</td></tr>
                <tr><th>Derived notes</th><td>{counts["derived"]}</td></tr>
                <tr><th>Vault root</th><td><code>{html.escape(root.as_posix())}</code></td></tr>
              </tbody>
            </table>
          </aside>
        </section>

        <section class="toc-box">
          <h2>Contents</h2>
          <div class="toc-columns">
            <ul>
              <li><a href="#collections">Collections</a></li>
              <li><a href="#research-areas">Research areas</a></li>
              <li><a href="#featured-sources">Featured source pages</a></li>
            </ul>
            <ul>
              <li><a href="#source-library">Source library</a></li>
              <li><a href="#concept-atlas">Concept atlas</a></li>
              <li><a href="#system-notes">System notes and derived work</a></li>
            </ul>
          </div>
        </section>

        <section class="portal-section" id="collections">
          <div class="portal-heading">
            <h2>Collections</h2>
            <p>The homepage is organized as a reference portal rather than a raw dump of the markdown index.</p>
          </div>
          <div class="portal-grid">
            {''.join(collections_html)}
          </div>
        </section>

        <section class="portal-section" id="research-areas">
          <div class="portal-heading">
            <h2>Research Areas</h2>
            <p>Concept pages are grouped by major research clusters so the wiki reads more like an encyclopedia than a file tree.</p>
          </div>
          <div class="portal-grid">
            {''.join(research_areas_html)}
          </div>
        </section>

        <section class="portal-section" id="featured-sources">
          <div class="portal-heading">
            <h2>Featured Source Pages</h2>
            <p>Recent or high-signal source pages that are good starting points for exploration.</p>
          </div>
          <div class="portal-grid">
            {''.join(featured_sources_html)}
          </div>
        </section>

        <section class="portal-section" id="source-library">
          <div class="portal-heading">
            <h2>Source Library</h2>
            <p>Compact index of compiled source pages.</p>
          </div>
          <ul class="catalog-grid">
            {''.join(source_library_html)}
          </ul>
        </section>

        <section class="portal-section" id="concept-atlas">
          <div class="portal-heading">
            <h2>Concept Atlas</h2>
            <p>Top concept pages and grouped browse lists.</p>
          </div>
          <div class="portal-grid concept-overview-grid">
            <article class="portal-box">
              <h3>Most Referenced Concepts</h3>
              <ul class="portal-list">{''.join(top_concept_links)}</ul>
            </article>
            <article class="portal-box">
              <h3>Browse by Group</h3>
              {''.join(concept_group_html)}
            </article>
          </div>
        </section>

        <section class="portal-section" id="system-notes">
          <div class="portal-heading">
            <h2>System Notes and Derived Work</h2>
            <p>Operational pages that define the compiler, schemas, health checks, and filed-back outputs.</p>
          </div>
          <div class="portal-grid">
            {''.join(system_html)}
          </div>
          <h3>Derived Notes</h3>
          <ul class="catalog-grid">
            {''.join(derived_html)}
          </ul>
        </section>

        <div class="footer">Exported from the local research wiki at <code>{html.escape(root.as_posix())}</code>.</div>
      </main>
    </div>
  </div>
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
    sidebar_html = render_sidebar(docs, export_path)
    title = str(doc["title"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · Research Wiki</title>
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      {sidebar_html}
    </aside>
    <div class="content-shell">
      <main class="content">
        <div class="breadcrumb"><span>{html.escape(breadcrumb)}</span></div>
        {body_html}
        <div class="footer">Exported from the local research wiki at <code>{html.escape(root.as_posix())}</code>.</div>
      </main>
    </div>
  </div>
</body>
</html>
"""


def render_search_page(docs: list[dict[str, object]], root: Path, search_index: dict[str, object]) -> str:
    export_path = Path("search.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    sidebar_html = render_sidebar(docs, export_path)
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
const records = JSON.parse(searchDataEl.textContent || '{"documents": []}').documents || [];

const tokenize = (query) =>
  query.toLowerCase().trim().split(/\\s+/).filter(Boolean);

const scoreRecord = (record, tokens) => {
  const title = record.title.toLowerCase();
  const aliases = (record.aliases || []).join(' ').toLowerCase();
  const meta = [record.group, record.note_type, record.year, record.venue, record.doi, record.arxiv_id]
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
  if (!tokens.length) {
    statusEl.textContent = 'Search title, aliases, concepts, DOI, arXiv, venue, or summaries.';
    resultsEl.innerHTML = '<div class="empty-state">Start typing to search the exported wiki.</div>';
    return;
  }
  const ranked = records
    .map((record) => ({ record, score: scoreRecord(record, tokens) }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || left.record.title.localeCompare(right.record.title))
    .slice(0, 30);
  statusEl.textContent = ranked.length
    ? `${ranked.length} result${ranked.length === 1 ? '' : 's'} for "${query}".`
    : `No results for "${query}".`;
  if (!ranked.length) {
    resultsEl.innerHTML = '<div class="empty-state">No matching pages yet. Try a concept name, author, DOI, venue, or year.</div>';
    return;
  }
  resultsEl.innerHTML = ranked.map(({ record }) => {
    const pills = [
      record.group,
      record.note_type,
      record.year,
      record.venue
    ].filter(Boolean).map((value) => `<span class="pill">${escapeHtml(String(value))}</span>`).join('');
    const ids = [
      record.doi ? `<span class="pill">DOI ${escapeHtml(record.doi)}</span>` : '',
      record.arxiv_id ? `<span class="pill">arXiv ${escapeHtml(record.arxiv_id)}</span>` : ''
    ].join('');
    return `
      <article class="result-card">
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
  const nextUrl = `${window.location.pathname}${nextParams.toString() ? `?${nextParams.toString()}` : ''}`;
  window.history.replaceState({}, '', nextUrl);
  renderCards(query);
};

const init = () => {
  const initialQuery = params.get('q') || '';
  searchInput.value = initialQuery;
  renderCards(initialQuery);
};

searchInput.addEventListener('input', updateSearch);
window.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement !== searchInput) {
    event.preventDefault();
    searchInput.focus();
  }
});

init();
""".strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Search The Wiki · Research Wiki</title>
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      {sidebar_html}
    </aside>
    <div class="content-shell">
      <main class="content">
        <div class="breadcrumb"><span>output/html/search.html</span></div>
        <section class="search-hero">
          <h1>Search The Wiki</h1>
          <p>Search across compiled pages, concept notes, derived notes, and bibliographic metadata like DOI, arXiv ID, venue, and year.</p>
        </section>
        <div class="search-box">
          <input type="search" data-search-input placeholder="Try: neural operators, 10.1038, arXiv 2210.06636, Science Advances" autofocus>
        </div>
        <div class="search-hint" data-search-status>Loading search index...</div>
        <section class="search-results" data-search-results></section>
        <div class="footer">Exported from the local research wiki at <code>{html.escape(root.as_posix())}</code>.</div>
      </main>
    </div>
  </div>
  <script id="search-index-data" type="application/json">{search_data}</script>
  <script>{script}</script>
</body>
</html>
"""


def render_ask_page(docs: list[dict[str, object]], root: Path) -> str:
    export_path = Path("ask.html")
    stylesheet_href = relative_href(Path("assets/wiki.css"), export_path)
    sidebar_html = render_sidebar(docs, export_path)
    server_command = ".venv/bin/python _meta/scripts/wiki_cli.py serve-html --root ."
    script = f"""
const formEl = document.querySelector('[data-ask-form]');
const textareaEl = document.querySelector('[data-ask-input]');
const submitEl = document.querySelector('[data-ask-submit]');
const statusEl = document.querySelector('[data-ask-status]');
const resultEl = document.querySelector('[data-ask-result]');
const metaEl = document.querySelector('[data-ask-meta]');
const fileIntoWikiEl = document.querySelector('[data-file-into-wiki]');
const serverNoteEl = document.querySelector('[data-server-note]');

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
    payload.output ? `Output: <code>${{escapeHtml(payload.output)}}</code>` : '',
    payload.filed_into_wiki ? `Filed into wiki: <code>${{escapeHtml(payload.filed_into_wiki)}}</code>` : '',
    payload.context_mode ? `Context mode: <code>${{escapeHtml(payload.context_mode)}}</code>` : '',
    Array.isArray(payload.context_files) && payload.context_files.length
      ? `Context files: ${{payload.context_files.slice(0, 8).map((item) => `<code>${{escapeHtml(item)}}</code>`).join(' ')}}`
      : ''
  ].filter(Boolean);
  metaEl.innerHTML = lines.join('<br>');
}};

const setUnavailable = () => {{
  serverNoteEl.hidden = false;
  statusEl.textContent = 'Q&A needs the local HTML server.';
  resultEl.textContent = `Run: {server_command}`;
  metaEl.innerHTML = '';
  submitEl.disabled = true;
}};

if (window.location.protocol === 'file:') {{
  setUnavailable();
}} else {{
  serverNoteEl.hidden = false;
  serverNoteEl.innerHTML = 'This page calls the local wiki server so your Claude API key stays on disk. If the form does not respond, start the server with <code>{server_command}</code>.';
}}

formEl.addEventListener('submit', async (event) => {{
  event.preventDefault();
  const question = textareaEl.value.trim();
  if (!question) {{
    statusEl.textContent = 'Enter a question first.';
    return;
  }}
  submitEl.disabled = true;
  statusEl.textContent = 'Asking the wiki...';
  resultEl.textContent = '';
  metaEl.innerHTML = '';
  try {{
    const response = await fetch('/api/ask', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        question,
        file_into_wiki: fileIntoWikiEl.checked
      }})
    }});
    const payload = await response.json();
    if (!response.ok) {{
      throw new Error(payload.error || 'Q&A request failed.');
    }}
    statusEl.textContent = 'Answer ready.';
    resultEl.textContent = payload.answer || '';
    renderMeta(payload);
  }} catch (error) {{
    console.error(error);
    statusEl.textContent = error.message || 'Q&A request failed.';
    resultEl.textContent = '';
    metaEl.innerHTML = '';
  }} finally {{
    submitEl.disabled = false;
  }}
}});
""".strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ask The Wiki · Research Wiki</title>
  <link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      {sidebar_html}
    </aside>
    <div class="content-shell">
      <main class="content">
        <div class="breadcrumb"><span>output/html/ask.html</span></div>
        <section class="search-hero">
          <h1>Ask The Wiki</h1>
          <p>Ask questions against the compiled vault and get a grounded answer from the same local pipeline that powers the CLI.</p>
        </section>
        <div class="ask-layout">
          <section class="ask-form">
            <form data-ask-form>
              <textarea data-ask-input placeholder="Try: Compare the neural operator papers in this vault."></textarea>
              <div class="ask-actions">
                <button class="primary-button" data-ask-submit type="submit">Ask</button>
                <label class="checkbox-row">
                  <input data-file-into-wiki type="checkbox">
                  <span>File the answer back into <code>wiki/derived</code></span>
                </label>
              </div>
            </form>
          </section>
          <div class="server-note" data-server-note hidden></div>
          <section class="answer-shell">
            <div class="search-hint" data-ask-status>Waiting for a question.</div>
            <div class="answer-meta" data-ask-meta></div>
            <pre class="answer-output" data-ask-result>Answers will appear here.</pre>
          </section>
        </div>
        <div class="footer">Exported from the local research wiki at <code>{html.escape(root.as_posix())}</code>.</div>
      </main>
    </div>
  </div>
  <script>{script}</script>
</body>
</html>
"""


def export_html(root: Path) -> dict[str, object]:
    config = load_config(root)
    export_root = root / config.get("html_dir", "output/html")
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True, exist_ok=True)
    (export_root / "assets").mkdir(parents=True, exist_ok=True)
    (export_root / "assets" / "wiki.css").write_text(STYLE_CSS + "\n", encoding="utf-8")

    docs, title_to_export, source_to_export = build_doc_index(root)
    search_index = build_search_index(root, docs)
    written = []
    for doc in docs:
        export_path = export_root / Path(doc["export_path"])
        export_path.parent.mkdir(parents=True, exist_ok=True)
        html_text = render_document_page(doc, docs, root, export_root, title_to_export, source_to_export)
        export_path.write_text(html_text, encoding="utf-8")
        written.append(export_path.relative_to(root).as_posix())

    search_index_path = export_root / "assets" / "search-index.json"
    search_index_path.write_text(json.dumps(search_index, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(search_index_path.relative_to(root).as_posix())

    search_page_path = export_root / "search.html"
    search_page_path.write_text(render_search_page(docs, root, search_index), encoding="utf-8")
    written.append(search_page_path.relative_to(root).as_posix())

    ask_page_path = export_root / "ask.html"
    ask_page_path.write_text(render_ask_page(docs, root), encoding="utf-8")
    written.append(ask_page_path.relative_to(root).as_posix())

    return {
        "export_root": export_root.relative_to(root).as_posix(),
        "entrypoint": (export_root / "index.html").relative_to(root).as_posix(),
        "search_page": search_page_path.relative_to(root).as_posix(),
        "ask_page": ask_page_path.relative_to(root).as_posix(),
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
