#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections.abc import Iterable
from pathlib import Path

from ask_wiki import ask_main
from export_html import export_html_main, parse_aliases
from export_okf import export_okf_main
from serve_html import serve_html_main
from zotero_import import add_zotero_arguments, run_zotero_args
from wiki_pipeline import (
    compile_main,
    convert_main,
    detect_title,
    lint_main,
    load_config,
    parse_root_arg,
    read_text,
    slugify,
    strip_frontmatter,
    timestamp_string,
    watch_main,
)


SEARCH_STOPWORDS = frozenset(
    """
    a an and are as at be by do for from has have how if in into is it its of on or
    than that the their then there these this to was were what when where which who
    why will with vs
    """.split()
)
# Field weights and per-term count caps. Caps stop long pages from winning by
# length alone; the body cap is the only length control (no character cutoff).
SEARCH_FIELD_WEIGHTS = {"title": 10, "aliases": 8, "headings": 3, "body": 1}
SEARCH_FIELD_CAPS = {"title": 2, "aliases": 4, "headings": 6, "body": 20}
SEARCH_PHRASE_BONUS = 20.0
SEARCH_SNIPPET_CHARS = 220
SEARCH_SNIPPET_LEAD = 60


def wiki_documents(root: Path, include_raw: bool = False) -> list[Path]:
    config = load_config(root)
    wiki_dir = root / config["wiki_dir"]
    paths = sorted(path for path in wiki_dir.glob("*.md") if path.is_file())
    paths.extend(sorted((root / config["source_notes_dir"]).glob("*.md")))
    paths.extend(sorted((root / config["concepts_dir"]).glob("*.md")))
    paths.extend(sorted((root / config.get("projects_dir", "wiki/projects")).glob("*.md")))
    paths.extend(sorted((root / config["derived_wiki_dir"]).glob("*.md")))
    if include_raw:
        raw_dir = root / config.get("raw_dir", "raw")
        paths.extend(sorted(path for path in raw_dir.rglob("*.md") if path.is_file()))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        if path.exists() and path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def normalize_phrase(text: str) -> str:
    """Lowercase and collapse every non-alphanumeric run to one space."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def search_terms(query: str) -> list[str]:
    """Query tokens: lowercase alphanumeric runs of length >= 2 (acronyms such as
    FE/CL/FR survive), function words dropped, order kept, duplicates removed.
    If every token is a function word the tokens are kept so the query still runs."""
    tokens = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) >= 2]
    kept = [token for token in tokens if token not in SEARCH_STOPWORDS] or tokens
    terms: list[str] = []
    for token in kept:
        if token not in terms:
            terms.append(token)
    return terms


def term_regex(term: str) -> str:
    """Word-boundary regex for one lowercase query token with a light plural stem.

    Boundaries are alphanumeric lookarounds instead of ``\\b`` so that underscores,
    dots and hyphens separate words: ``SHIPYARD_TANK_V17`` contains ``v17``,
    ``T.BULKHEAD`` contains ``bulkhead``, ``physics-informed`` contains ``informed``,
    while ``surrogate`` does not contain ``gate`` and ``meshgraphnet`` does not
    contain ``net``. The stem accepts singular/plural pairs (slot/slots,
    mesh/meshes, taxonomy/taxonomies) in either direction.
    """
    stem = term
    if len(term) > 4 and term.endswith("ies"):
        stem = term[:-3] + "y"
    elif len(term) > 3 and term.endswith("s") and not term.endswith(("ss", "us", "is")):
        stem = term[:-1]
    if len(stem) > 3 and stem.endswith("y"):
        core = re.escape(stem[:-1]) + "(?:y|ies)"
    elif len(stem) >= 3:
        core = re.escape(stem) + "(?:s|es)?"
    else:
        core = re.escape(stem)
    return rf"(?<![a-z0-9]){core}(?![a-z0-9])"


def search_patterns(terms: list[str]) -> dict[str, re.Pattern[str]]:
    return {term: re.compile(term_regex(term)) for term in terms}


def search_headings(body: str) -> str:
    return "\n".join(
        match.group(1).strip()
        for match in re.finditer(r"^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", body, re.MULTILINE)
    )


def search_document(root: Path, path: Path) -> dict[str, object]:
    text = read_text(path)
    title = detect_title(text, path)
    aliases = parse_aliases(text)
    body = strip_frontmatter(text)
    phrases = {normalize_phrase(title)} | {normalize_phrase(alias) for alias in aliases}
    phrases.discard("")
    return {
        "path": path.relative_to(root).as_posix(),
        "title": title,
        "aliases": aliases,
        "body": body or text,
        "phrases": phrases,
        "fields": {
            "title": title.lower(),
            "aliases": "\n".join(aliases).lower(),
            "headings": search_headings(body).lower(),
            "body": body.lower(),
        },
    }


def search_term_counts(
    fields: dict[str, str], patterns: dict[str, re.Pattern[str]]
) -> dict[str, dict[str, int]]:
    return {
        term: {name: len(pattern.findall(value)) for name, value in fields.items()}
        for term, pattern in patterns.items()
    }


def search_rarity(all_counts: list[dict[str, dict[str, int]]], terms: list[str]) -> dict[str, float]:
    """Per-term weight log(1 + N/df) over the corpus of this call. Terms that occur
    in no document are omitted so they neither score nor count as unmatched."""
    total_docs = len(all_counts)
    rarity: dict[str, float] = {}
    for term in terms:
        document_frequency = sum(1 for counts in all_counts if any(counts[term].values()))
        if document_frequency:
            rarity[term] = math.log(1 + total_docs / document_frequency)
    return rarity


def search_score(
    counts: dict[str, dict[str, int]], rarity: dict[str, float], phrase_match: bool = False
) -> tuple[float, int]:
    """Field-weighted, capped, rarity-scaled term score; +SEARCH_PHRASE_BONUS when the
    whole query equals the title or an alias; the total is multiplied by
    (matched_terms / total_terms) ** 2 so documents holding every term win."""
    score = 0.0
    matched = 0
    for term, weight in rarity.items():
        per_field = counts.get(term, {})
        contribution = sum(
            SEARCH_FIELD_WEIGHTS[name] * min(per_field.get(name, 0), SEARCH_FIELD_CAPS[name])
            for name in SEARCH_FIELD_WEIGHTS
        )
        if contribution > 0:
            matched += 1
            score += contribution * weight
    if phrase_match:
        score += SEARCH_PHRASE_BONUS
    if rarity:
        score *= (matched / len(rarity)) ** 2
    return score, matched


def search_snippet(text: str, patterns: Iterable[re.Pattern[str]]) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    lower = compact.lower()
    positions = [match.start() for match in (pattern.search(lower) for pattern in patterns) if match]
    if not positions:
        return compact[:SEARCH_SNIPPET_CHARS]
    start = max(min(positions) - SEARCH_SNIPPET_LEAD, 0)
    return compact[start : start + SEARCH_SNIPPET_CHARS]


def search_wiki(root: Path, query: str, limit: int, include_raw: bool = False) -> dict[str, object]:
    terms = search_terms(query)
    if not terms:
        return {"query": query, "results": []}
    patterns = search_patterns(terms)
    documents = [search_document(root, path) for path in wiki_documents(root, include_raw=include_raw)]
    all_counts = [search_term_counts(doc["fields"], patterns) for doc in documents]
    rarity = search_rarity(all_counts, terms)
    if not rarity:
        return {"query": query, "results": []}
    phrase = normalize_phrase(query)
    hits = []
    for doc, counts in zip(documents, all_counts):
        score, _matched = search_score(counts, rarity, bool(phrase) and phrase in doc["phrases"])
        if score <= 0:
            continue
        hits.append(
            {
                "path": doc["path"],
                "title": doc["title"],
                "score": round(score, 2),
                "snippet": search_snippet(str(doc["body"]), patterns.values()),
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
    search_parser.add_argument(
        "--include-raw",
        action="store_true",
        help="also search raw/**/*.md (default: wiki pages only)",
    )
    search_parser.add_argument("query", nargs="+")

    file_parser = subparsers.add_parser("file-output")
    file_parser.add_argument("--root", default=None)
    file_parser.add_argument("--name", default=None)
    file_parser.add_argument("path")

    html_parser = subparsers.add_parser("export-html")
    html_parser.add_argument("--root", default=None)

    okf_parser = subparsers.add_parser("export-okf")
    okf_parser.add_argument("--root", default=None)

    serve_parser = subparsers.add_parser("serve-html")
    serve_parser.add_argument("--root", default=None)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    zotero_parser = subparsers.add_parser(
        "zotero-import",
        help="copy PDFs from a local Zotero collection into a source directory",
    )
    add_zotero_arguments(zotero_parser)

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
        result = search_wiki(root, query, args.limit, include_raw=args.include_raw)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "file-output":
        root = parse_root_arg(args.root)
        result = file_output(root, args.path, args.name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "export-html":
        return export_html_main(["--root", str(parse_root_arg(args.root))])

    if args.command == "export-okf":
        return export_okf_main(["--root", str(parse_root_arg(args.root))])

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

    if args.command == "zotero-import":
        return run_zotero_args(args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
