#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from wiki_pipeline import (
    DEFAULT_ROOT,
    append_log_entry,
    detect_title,
    load_config,
    parse_root_arg,
    read_text,
    render_yaml_list,
    slugify,
    timestamp_string,
    today_string,
    top_terms,
    write_text_if_changed,
)

# ChatGPT.app bundles moved the CLI from Resources/codex to Resources/codex-cli/bin/codex (Sept 2026).
CODEX_CLI_CANDIDATES = tuple(
    app_dir / "Contents/Resources" / relative
    for app_dir in (Path("/Applications/ChatGPT.app"), Path.home() / "Applications/ChatGPT.app")
    for relative in ("codex-cli/bin/codex", "codex")
)


def collect_wiki_documents(root: Path) -> list[dict[str, Any]]:
    config = load_config(root)
    wiki_dir = root / config["wiki_dir"]
    concepts_dir = root / config["concepts_dir"]
    sources_dir = root / config["source_notes_dir"]
    derived_dir = root / config["derived_wiki_dir"]
    projects_dir = root / config.get("projects_dir", "wiki/projects")

    docs = []
    top_level_priority = {
        "INDEX.md": 100,
        "LOG.md": 90,
        "SYSTEM_OVERVIEW.md": 80,
        "PAGE_FORMATS.md": 78,
        "PAPER_TEMPLATE.md": 76,
        "LINT_AND_HEAL.md": 70,
        "DASHBOARD.md": 30,
    }
    for path in sorted(wiki_dir.glob("*.md")):
        if path.exists():
            text = read_text(path)
            docs.append({"path": path, "title": detect_title(text, path), "text": text, "priority": top_level_priority.get(path.name, 50)})

    for path in sorted(sources_dir.glob("*.md")):
        text = read_text(path)
        docs.append({"path": path, "title": detect_title(text, path), "text": text, "priority": 65})

    for path in sorted(concepts_dir.glob("*.md")):
        text = read_text(path)
        docs.append({"path": path, "title": detect_title(text, path), "text": text, "priority": 60})

    for path in sorted(projects_dir.glob("*.md")):
        text = read_text(path)
        docs.append({"path": path, "title": detect_title(text, path), "text": text, "priority": 75})

    for path in sorted(derived_dir.glob("*.md")):
        text = read_text(path)
        docs.append({"path": path, "title": detect_title(text, path), "text": text, "priority": 40})

    return docs


def query_terms(question: str) -> list[str]:
    terms = set(top_terms(question, limit=10))
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", question.lower()):
        terms.add(token)
    return sorted(terms)


def score_document(question_terms: list[str], document: dict[str, Any]) -> int:
    text = f"{document['title']}\n{document['text'][:20000]}".lower()
    score = int(document.get("priority", 0))
    for term in question_terms:
        score += text.count(term)
        if term in document["title"].lower():
            score += 5
    return score


def select_context(root: Path, question: str) -> tuple[list[dict[str, Any]], str]:
    config = load_config(root)
    char_limit = int(config.get("qa_context_char_limit", 180000))
    max_docs = int(config.get("qa_top_concepts", 14))
    docs = collect_wiki_documents(root)
    total_chars = sum(len(doc["text"]) for doc in docs)
    if total_chars <= char_limit:
        return docs, "full-wiki"

    terms = query_terms(question)
    scored = []
    for doc in docs:
        scored.append((score_document(terms, doc), doc))
    scored.sort(key=lambda item: (-item[0], item[1]["title"].lower()))

    selected = []
    current_chars = 0
    for score, doc in scored:
        if score <= 0:
            continue
        if len(selected) >= max_docs:
            break
        if current_chars and current_chars + len(doc["text"]) > char_limit:
            continue
        selected.append(doc)
        current_chars += len(doc["text"])

    if not selected:
        selected = docs[: min(len(docs), max_docs)]
    return selected, "focused-wiki"


def build_prompt(question: str, output_format: str, context_mode: str, context_docs: list[dict[str, Any]]) -> str:
    source_list = "\n".join(f"- {doc['path'].name}: {doc['title']}" for doc in context_docs)
    base = [
        "You are answering a question against a maintained markdown wiki compiled from raw research documents.",
        f"The context selection mode is `{context_mode}`.",
        "Use only the provided wiki context. If something is uncertain, say so plainly.",
        "When citing local wiki notes, prefer Obsidian wiki-links with note titles, such as [[System Overview]] or [[Lint + Heal]].",
        "",
        "Context files:",
        source_list,
        "",
        f"Question: {question}",
        "",
    ]
    if output_format == "marp":
        base.extend(
            [
                "Return a Marp markdown deck.",
                "Start with Marp frontmatter.",
                "Keep the deck concise, presentation-ready, and grounded in the provided wiki context.",
            ]
        )
    else:
        base.extend(
            [
                "Return markdown only.",
                "Use sections named `## Answer`, `## Evidence`, and `## Open Questions` when useful.",
            ]
        )
    return "\n".join(base)


def resolve_codex_cli(root: Path) -> str:
    config = load_config(root)
    configured = str(config.get("codex_cli", "codex")).strip() or "codex"
    configured_path = Path(configured).expanduser()
    if configured_path.is_file():
        return str(configured_path)
    resolved = shutil.which(configured)
    if resolved:
        return resolved
    for candidate in CODEX_CLI_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    checked = ", ".join(str(path) for path in CODEX_CLI_CANDIDATES)
    raise RuntimeError(f"Codex CLI is unavailable. Checked PATH and: {checked}")


def codex_subscription_status(root: Path) -> dict[str, str]:
    codex_cli = resolve_codex_cli(root)
    try:
        result = subprocess.run(
            [codex_cli, "login", "status"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Codex login status check timed out.") from exc
    details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode != 0 or "Logged in using ChatGPT" not in details:
        raise RuntimeError(f"Codex is not logged in through ChatGPT. {details or 'No login status returned.'}")
    return {
        "status": "ok",
        "provider": "codex-subscription",
        "auth": "chatgpt",
        "codex_cli": codex_cli,
    }


def ask_codex(root: Path, question: str, output_format: str) -> tuple[str, list[dict[str, Any]], str]:
    config = load_config(root)
    auth = codex_subscription_status(root)
    docs, context_mode = select_context(root, question)
    prompt = build_prompt(question, output_format, context_mode, docs)
    context_chunks = []
    for doc in docs:
        context_chunks.append(f"# {doc['title']}\nPath: {doc['path'].relative_to(root).as_posix()}\n\n{doc['text']}")
    request = prompt + "\n\nWiki context:\n\n" + "\n\n".join(context_chunks)
    timeout_seconds = float(config.get("qa_timeout_seconds", 300))
    codex_cli = auth["codex_cli"]

    with tempfile.TemporaryDirectory(prefix="research-wiki-codex-") as temp_dir:
        response_path = Path(temp_dir) / "answer.md"
        command = [
            codex_cli,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-last-message",
            str(response_path),
            "-",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=root,
                input=request,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex subscription request timed out after {timeout_seconds:g}s.") from exc

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Unknown Codex CLI error.").strip()
            raise RuntimeError(f"Codex subscription request failed: {details[-1600:]}")
        answer = response_path.read_text(encoding="utf-8").strip() if response_path.exists() else ""

    if not answer:
        raise RuntimeError("Codex returned no answer text.")
    return answer, docs, context_mode


def render_answer_file(root: Path, question: str, answer: str, docs: list[dict[str, Any]], context_mode: str) -> str:
    lines = [
        "---",
        f"title: {json.dumps(question[:120], ensure_ascii=False)}",
        f"generated_at: {today_string()}",
        f"context_mode: {json.dumps(context_mode)}",
        *render_yaml_list("context_files", [doc["path"].relative_to(root).as_posix() for doc in docs]),
        "---",
        "",
        f"# {question}",
        "",
        answer.strip(),
        "",
    ]
    return "\n".join(lines)


def output_path(root: Path, question: str, output_format: str) -> Path:
    config = load_config(root)
    timestamp = timestamp_string().replace(":", "-")
    safe_name = slugify(question)[:80] or "query"
    if output_format == "marp":
        return root / config["slides_dir"] / f"{timestamp}-{safe_name}.md"
    return root / config["answers_dir"] / f"{timestamp}-{safe_name}.md"


def file_back_into_wiki(root: Path, source_path: Path) -> Path:
    config = load_config(root)
    destination = root / config["derived_wiki_dir"] / source_path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination = destination.with_name(f"{destination.stem}-{timestamp_string().replace(':', '-')}{destination.suffix}")
    shutil.copy2(source_path, destination)
    return destination


def run_question(root: Path, question: str, output_format: str = "markdown", file_into_wiki: bool = False) -> dict[str, Any]:
    answer, docs, context_mode = ask_codex(root, question, output_format)
    rendered = render_answer_file(root, question, answer, docs, context_mode)

    destination = output_path(root, question, output_format)
    write_text_if_changed(destination, rendered)

    filed_path = None
    if file_into_wiki:
        filed_path = file_back_into_wiki(root, destination)

    payload: dict[str, Any] = {
        "question": question,
        "answer": answer,
        "output": destination.relative_to(root).as_posix(),
        "provider": "codex-subscription",
        "context_mode": context_mode,
        "context_files": [doc["path"].relative_to(root).as_posix() for doc in docs],
    }
    if filed_path is not None:
        payload["filed_into_wiki"] = filed_path.relative_to(root).as_posix()

    append_log_entry(
        root,
        "query",
        question[:120],
        [
            f"Output: {destination.relative_to(root).as_posix()}",
            "Provider: Codex via ChatGPT subscription",
            f"Context mode: {context_mode}",
            f"Context files: {', '.join(doc['path'].relative_to(root).as_posix() for doc in docs[:8])}",
            *([f"Filed back into wiki: {filed_path.relative_to(root).as_posix()}"] if filed_path is not None else []),
        ],
    )
    return payload


def ask_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="+")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--format", choices=("markdown", "marp"), default="markdown")
    parser.add_argument("--file-into-wiki", action="store_true")
    args = parser.parse_args(argv)

    root = parse_root_arg(args.root)
    question = " ".join(args.question).strip()
    result = run_question(root, question, output_format=args.format, file_into_wiki=args.file_into_wiki)
    payload = {key: value for key, value in result.items() if key != "answer"}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(ask_main())
