#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from ask_wiki import ask_main
from export_html import export_html_main
from serve_html import serve_html_main
from wiki_pipeline import (
    compile_main,
    convert_main,
    detect_title,
    lint_main,
    load_config,
    parse_root_arg,
    read_text,
    slugify,
    timestamp_string,
    top_terms,
    watch_main,
)


def wiki_documents(root: Path) -> list[Path]:
    config = load_config(root)
    wiki_dir = root / config["wiki_dir"]
    paths = sorted(path for path in wiki_dir.glob("*.md") if path.is_file())
    paths.extend(sorted((root / config["source_notes_dir"]).glob("*.md")))
    paths.extend(sorted((root / config["concepts_dir"]).glob("*.md")))
    paths.extend(sorted((root / config["derived_wiki_dir"]).glob("*.md")))
    return [path for path in paths if path.exists()]


def search_terms(query: str) -> list[str]:
    terms = set(top_terms(query, limit=10))
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", query.lower()):
        terms.add(token)
    return sorted(terms)


def search_score(text: str, title: str, terms: list[str]) -> int:
    haystack = f"{title}\n{text[:20000]}".lower()
    score = 0
    for term in terms:
        score += haystack.count(term)
        if term in title.lower():
            score += 5
    return score


def search_snippet(text: str, terms: list[str]) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    lower = compact.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    if not positions:
        return compact[:220]
    start = max(min(positions) - 60, 0)
    end = min(start + 220, len(compact))
    return compact[start:end]


def search_wiki(root: Path, query: str, limit: int) -> dict[str, object]:
    terms = search_terms(query)
    hits = []
    for path in wiki_documents(root):
        text = read_text(path)
        title = detect_title(text, path)
        score = search_score(text, title, terms)
        if score <= 0:
            continue
        hits.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": title,
                "score": score,
                "snippet": search_snippet(text, terms),
            }
        )
    hits.sort(key=lambda item: (-item["score"], item["title"].lower()))
    return {"query": query, "results": hits[:limit]}


def file_output(root: Path, source: str, name: str | None) -> dict[str, str]:
    config = load_config(root)
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    suffix = source_path.suffix or ".md"
    stem = slugify(name or source_path.stem) or source_path.stem
    destination_dir = root / config["derived_wiki_dir"]
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{stem}{suffix}"
    if destination.exists():
        destination = destination_dir / f"{stem}-{timestamp_string().replace(':', '-')}{suffix}"
    shutil.copy2(source_path, destination)
    return {
        "source": source_path.as_posix(),
        "filed_into_wiki": destination.relative_to(root).as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--root", default=None)
    compile_parser.add_argument("--force", action="store_true")

    convert_parser = subparsers.add_parser("convert")
    convert_parser.add_argument("--root", default=None)
    convert_parser.add_argument("--force", action="store_true")

    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--root", default=None)
    watch_parser.add_argument("--interval", type=int, default=None)
    watch_parser.add_argument("--once", action="store_true")
    watch_parser.add_argument("--force", action="store_true")

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("--root", default=None)

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("--root", default=None)
    ask_parser.add_argument("--format", choices=("markdown", "marp"), default="markdown")
    ask_parser.add_argument("--file-into-wiki", action="store_true")
    ask_parser.add_argument("question", nargs="+")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--root", default=None)
    search_parser.add_argument("--limit", type=int, default=8)
    search_parser.add_argument("query", nargs="+")

    file_parser = subparsers.add_parser("file-output")
    file_parser.add_argument("--root", default=None)
    file_parser.add_argument("--name", default=None)
    file_parser.add_argument("path")

    html_parser = subparsers.add_parser("export-html")
    html_parser.add_argument("--root", default=None)

    serve_parser = subparsers.add_parser("serve-html")
    serve_parser.add_argument("--root", default=None)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if args.command == "compile":
        forwarded = ["--root", str(parse_root_arg(args.root))]
        if args.force:
            forwarded.append("--force")
        return compile_main(forwarded)

    if args.command == "convert":
        forwarded = ["--root", str(parse_root_arg(args.root))]
        if args.force:
            forwarded.append("--force")
        return convert_main(forwarded)

    if args.command == "watch":
        forwarded = ["--root", str(parse_root_arg(args.root))]
        if args.interval is not None:
            forwarded.extend(["--interval", str(args.interval)])
        if args.once:
            forwarded.append("--once")
        if args.force:
            forwarded.append("--force")
        return watch_main(forwarded)

    if args.command == "lint":
        return lint_main(["--root", str(parse_root_arg(args.root))])

    if args.command == "ask":
        forwarded = ["--root", str(parse_root_arg(args.root)), "--format", args.format]
        if args.file_into_wiki:
            forwarded.append("--file-into-wiki")
        forwarded.extend(args.question)
        return ask_main(forwarded)

    if args.command == "search":
        root = parse_root_arg(args.root)
        query = " ".join(args.query).strip()
        result = search_wiki(root, query, args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "file-output":
        root = parse_root_arg(args.root)
        result = file_output(root, args.path, args.name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "export-html":
        return export_html_main(["--root", str(parse_root_arg(args.root))])

    if args.command == "serve-html":
        return serve_html_main(
            [
                "--root",
                str(parse_root_arg(args.root)),
                "--host",
                args.host,
                "--port",
                str(args.port),
            ]
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
