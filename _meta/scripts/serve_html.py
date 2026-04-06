#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ask_wiki import run_question
from export_html import export_html
from wiki_pipeline import load_config, parse_root_arg


class WikiHtmlHandler(SimpleHTTPRequestHandler):
    root: Path

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/health":
            self._send_json({"status": "ok"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/ask":
            self._send_json({"error": "Not found."}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
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
                "context_mode": result["context_mode"],
                "context_files": result["context_files"],
                "filed_into_wiki": result.get("filed_into_wiki"),
            }
        )


def serve_html(root: Path, host: str = "127.0.0.1", port: int = 8765) -> int:
    export_html(root)
    config = load_config(root)
    export_root = root / config.get("html_dir", "output/html")

    WikiHtmlHandler.root = root
    handler = partial(WikiHtmlHandler, directory=str(export_root))
    server = ThreadingHTTPServer((host, port), handler)
    print(json.dumps({"url": f"http://{host}:{port}", "export_root": export_root.relative_to(root).as_posix()}, ensure_ascii=False))
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
