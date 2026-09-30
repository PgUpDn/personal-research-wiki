"""Shared, offline-ready navigation for the research wiki HTML export."""

from __future__ import annotations

import html
import os
from pathlib import Path


ICONS = {
    "overview": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "search": '<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
    "ask": '<path d="M21 11.5a8.3 8.3 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.3 8.3 0 0 1-3.8-.9L3 21l1.9-5.7a8.3 8.3 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.3 8.3 0 0 1 3.8-.9H13a8.5 8.5 0 0 1 8 8z"/><path d="M8 11h8m-8 4h5"/>',
    "map": '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><path d="m10.5 7.5-4 9m7-9 4 9M8 19h8"/>',
    "sources": '<path d="M4 3h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-2H4zM20 3h-4a3 3 0 0 0-3 3v15a4 4 0 0 1 4-2h3z"/>',
    "concepts": '<path d="m12 3 9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    "projects": '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3z"/>',
    "notes": '<path d="M14 3H5v18h14V8zM14 3v5h5M8 12h8M8 16h6"/>',
    "system": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.01"/>',
    "arrow": '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
}


def icon(name: str) -> str:
    return f'<svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, ICONS["notes"])}</svg>'


def render_workspace_shell(docs: list[dict[str, object]], current: Path, title: str) -> str:
    def href(target: str) -> str:
        path, separator, query = target.partition("?")
        relative = Path(os.path.relpath(Path(path), current.parent)).as_posix()
        return html.escape(relative + (separator + query if separator else ""), quote=True)

    counts = {group: sum(doc["group"] == group for doc in docs) for group in ("Sources", "Concepts", "Derived")}

    def item(label: str, target: str, glyph: str, active: bool = False, count: int | None = None) -> str:
        count_html = f'<small class="nav-count">{count}</small>' if count is not None else ""
        current_attr = ' aria-current="page"' if active else ""
        return f'<a class="nav-item{" current" if active else ""}" href="{href(target)}"{current_attr}>{icon(glyph)}<span>{label}</span>{count_html}</a>'

    navigation = [
        '<p class="nav-caption">Workspace</p>',
        item("Overview", "index.html", "overview", current == Path("index.html")),
        item("Search library", "search.html", "search", current == Path("search.html")),
        item("Ask the Wiki", "ask.html", "ask", current == Path("ask.html")),
        item("Knowledge map", "knowledge.html", "map", current == Path("knowledge.html")),
        '<p class="nav-caption">Library</p>',
        item("Sources", "search.html?group=Sources", "sources", current.parts[0] == "sources", counts["Sources"]),
        item("Concepts", "search.html?group=Concepts", "concepts", current.parts[0] == "concepts", counts["Concepts"]),
        item("Research notes", "search.html?group=Derived", "notes", current.parts[0] == "derived", counts["Derived"]),
        '<p class="nav-caption">Projects</p><div class="project-nav">',
    ]
    projects = sorted((doc for doc in docs if doc.get("note_type") == "project"), key=lambda doc: (
        str(doc.get("parent_project_id") or doc.get("project_id") or doc["title"]).lower(),
        bool(doc.get("parent_project_id")), str(doc["title"]).lower(),
    ))
    for doc in projects:
        path = Path(doc["export_path"])
        name = str(doc.get("project_name") or doc["title"])
        if not doc.get("parent_project_id"):
            name = str(doc.get("project_id") or name)
            name = "Physics Foundation Model" if name == "pfm" else name
        else:
            name = name.split(" (", 1)[0].replace("_", " ")
        classes = "project-nav-item"
        classes += " subproject" if doc.get("parent_project_id") else ""
        classes += " current" if path == current else ""
        active_attr = ' aria-current="page"' if path == current else ""
        navigation.append(f'<a class="{classes}" href="{href(path.as_posix())}"{active_attr}><span class="project-dot"></span><span>{html.escape(name)}</span></a>')
    navigation.append('</div>')
    if any(Path(doc["export_path"]) == Path("projects/README.html") for doc in docs):
        navigation.append(item("All projects", "projects/README.html", "projects", current == Path("projects/README.html")))
    system = ""
    if any(Path(doc["export_path"]) == Path("SYSTEM_OVERVIEW.html") for doc in docs):
        system = item("About this wiki", "SYSTEM_OVERVIEW.html", "system", current == Path("SYSTEM_OVERVIEW.html"))
    group = "Workspace" if current.parent == Path(".") else current.parts[0].title()
    return f'''<a class="skip-link" href="#main-content">Skip to content</a>
<aside class="workspace-sidebar" id="workspace-nav">
  <a class="workspace-brand" href="{href("index.html")}"><span class="brand-mark">rw<span>.</span></span><span class="brand-name"><strong>Research Wiki</strong><small>RESEARCH WORKSPACE</small></span></a>
  <nav class="workspace-nav" aria-label="Primary navigation">{''.join(navigation)}</nav>
  <div class="sidebar-bottom">{system}<div class="workspace-owner"><span class="owner-avatar">RW</span><span>My research<small>Personal workspace</small></span></div></div>
</aside>
<button type="button" class="nav-scrim" aria-label="Close navigation" tabindex="-1"></button>
<header class="workspace-topbar">
  <button type="button" class="mobile-toggle" aria-label="Open navigation" aria-expanded="false" aria-controls="workspace-nav">{icon("menu")}</button>
  <div class="topbar-crumb"><span>{group}</span><span class="crumb-divider">/</span><strong>{html.escape(title)}</strong></div>
  <div class="topbar-tools"><a class="topbar-search" href="{href("search.html")}" aria-label="Search library">{icon("search")}<span>Search anything</span><kbd>/</kbd></a><span class="local-badge">Local workspace</span></div>
</header>'''
