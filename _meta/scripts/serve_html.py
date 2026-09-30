#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hmac
import json
import secrets
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Mapping
from urllib.parse import urlsplit

from ask_wiki import codex_subscription_status, run_question
from export_html import export_html
from wiki_pipeline import load_config, parse_root_arg


LOCAL_SERVER_HOSTS = {"127.0.0.1", "localhost", "::1"}


def is_same_origin_local_request(headers: Mapping[str, str]) -> bool:
    host = str(headers.get("Host", "")).strip().lower()
    if not host:
        return False
    try:
        hostname = urlsplit(f"http://{host}").hostname
    except ValueError:
        return False
    if hostname not in LOCAL_SERVER_HOSTS:
        return False

    fetch_site = str(headers.get("Sec-Fetch-Site", "")).strip().lower()
    if fetch_site == "same-origin":
        return True

    for header_name in ("Origin", "Referer"):
        value = str(headers.get(header_name, "")).strip()
        if not value or value == "null":
            continue
        try:
            parsed = urlsplit(value)
        except ValueError:
            continue
        if parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host:
            return True
    return False


class WikiHtmlHandler(SimpleHTTPRequestHandler):
    root: Path
    api_token: str

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:
        self.send_response(405)
        self.end_headers()

    def _authorized(self) -> bool:
        supplied = self.headers.get("X-Wiki-Token", "")
        if hmac.compare_digest(supplied, self.api_token) or is_same_origin_local_request(self.headers):
            return True
        self._send_json({"error": "Unauthorized."}, status=401)
        return False

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/health":
            if not self._authorized():
                return
            try:
                status = codex_subscription_status(self.root)
            except Exception as exc:
                self._send_json({"status": "error", "provider": "codex-subscription", "error": str(exc)}, status=503)
                return
            self._send_json({key: value for key, value in status.items() if key != "codex_cli"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/ask":
            self._send_json({"error": "Not found."}, status=404)
            return
        if not self._authorized():
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > 16_384:
            self._send_json({"error": "Request body is too large."}, status=413)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON."}, status=400)
            return

        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json({"error": "Question is required."}, status=400)
            return
        if len(question) > 8_000:
            self._send_json({"error": "Question is too long."}, status=400)
            return

        file_into_wiki = bool(payload.get("file_into_wiki"))
        try:
            result = run_question(self.root, question, output_format="markdown", file_into_wiki=file_into_wiki)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)
            return

        self._send_json(
            {
                "question": result["question"],
                "answer": result["answer"],
                "output": result["output"],
                "provider": result["provider"],
                "context_mode": result["context_mode"],
                "context_files": result["context_files"],
                "filed_into_wiki": result.get("filed_into_wiki"),
            }
        )


def serve_html(root: Path, host: str = "127.0.0.1", port: int = 8765) -> int:
    config = load_config(root)
    export_root = root / config.get("html_dir", "output/html")
    needs_initial_export = not (export_root / "index.html").is_file()
    if needs_initial_export:
        export_html(root)

    WikiHtmlHandler.root = root
    WikiHtmlHandler.api_token = secrets.token_urlsafe(32)
    handler = partial(WikiHtmlHandler, directory=str(export_root))
    server = ThreadingHTTPServer((host, port), handler)
    print(
        json.dumps(
            {
                "url": f"http://{host}:{port}/ask.html?wiki_token={WikiHtmlHandler.api_token}",
                "export_root": export_root.relative_to(root).as_posix(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if not needs_initial_export:
        def refresh_export() -> None:
            try:
                export_html(root)
            except Exception as exc:
                print(json.dumps({"event": "background-export-failed", "error": str(exc)}), file=sys.stderr, flush=True)

        Thread(target=refresh_export, name="research-wiki-export", daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def serve_html_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    return serve_html(parse_root_arg(args.root), host=args.host, port=args.port)


if __name__ == "__main__":
    raise SystemExit(serve_html_main())
