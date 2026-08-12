from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ask_wiki import ask_codex, codex_subscription_status, collect_wiki_documents, resolve_codex_cli


class AskCodexTests(unittest.TestCase):
    def test_project_pages_are_available_to_ask_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_path = root / "wiki/projects/example-programme.md"
            project_path.parent.mkdir(parents=True)
            project_path.write_text(
                "---\ntitle: Example Research Programme\nnote_type: project\n---\n\n# Example Research Programme\n",
                encoding="utf-8",
            )

            docs = collect_wiki_documents(root)

            project_doc = next(doc for doc in docs if doc["path"] == project_path)
            self.assertEqual(project_doc["priority"], 75)

    def test_subscription_status_confirms_chatgpt_login(self) -> None:
        completed = subprocess.CompletedProcess(
            ["/Applications/ChatGPT.app/Contents/Resources/codex", "login", "status"],
            0,
            "Logged in using ChatGPT\n",
            "",
        )
        with (
            patch(
                "ask_wiki.resolve_codex_cli",
                return_value="/Applications/ChatGPT.app/Contents/Resources/codex",
            ),
            patch("ask_wiki.subprocess.run", return_value=completed),
        ):
            status = codex_subscription_status(Path("/tmp"))
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["provider"], "codex-subscription")
        self.assertEqual(status["auth"], "chatgpt")

    def test_subscription_status_rejects_api_key_authentication(self) -> None:
        completed = subprocess.CompletedProcess(
            ["codex", "login", "status"],
            0,
            "Logged in using an API key\n",
            "",
        )
        with (
            patch("ask_wiki.resolve_codex_cli", return_value="codex"),
            patch("ask_wiki.subprocess.run", return_value=completed),
        ):
            with self.assertRaisesRegex(RuntimeError, "not logged in through ChatGPT"):
                codex_subscription_status(Path("/tmp"))

    def test_resolve_codex_cli_uses_chatgpt_bundle_when_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundled_cli = root / "ChatGPT.app" / "Contents" / "Resources" / "codex"
            bundled_cli.parent.mkdir(parents=True)
            bundled_cli.touch()
            with (
                patch("ask_wiki.load_config", return_value={"codex_cli": "codex"}),
                patch("ask_wiki.shutil.which", return_value=None),
                patch("ask_wiki.CODEX_CLI_CANDIDATES", (bundled_cli,)),
            ):
                self.assertEqual(resolve_codex_cli(root), str(bundled_cli))

    def test_ask_codex_uses_ephemeral_subscription_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "wiki" / "sources" / "example.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("# Example\n\nGrounded context.", encoding="utf-8")
            docs = [{"path": source_path, "title": "Example", "text": source_path.read_text(encoding="utf-8")}]
            invocation: dict[str, object] = {}

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                invocation["command"] = command
                invocation["input"] = kwargs["input"]
                output_path = Path(command[command.index("--output-last-message") + 1])
                output_path.write_text("## Answer\n\nGrounded response.", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch("ask_wiki.load_config", return_value={"codex_cli": "codex", "qa_timeout_seconds": 300}),
                patch("ask_wiki.select_context", return_value=(docs, "focused-wiki")),
                patch(
                    "ask_wiki.codex_subscription_status",
                    return_value={
                        "status": "ok",
                        "provider": "codex-subscription",
                        "auth": "chatgpt",
                        "codex_cli": "/Applications/ChatGPT.app/Contents/Resources/codex",
                    },
                ),
                patch("ask_wiki.subprocess.run", side_effect=fake_run),
            ):
                answer, selected, context_mode = ask_codex(root, "What does it say?", "markdown")

            command = invocation["command"]
            self.assertIsInstance(command, list)
            self.assertIn("--ephemeral", command)
            self.assertIn("--ignore-user-config", command)
            self.assertIn("--ignore-rules", command)
            self.assertIn("read-only", command)
            self.assertEqual(command[-1], "-")
            self.assertIn("Grounded context.", str(invocation["input"]))
            self.assertEqual(answer, "## Answer\n\nGrounded response.")
            self.assertEqual(selected, docs)
            self.assertEqual(context_mode, "focused-wiki")


if __name__ == "__main__":
    unittest.main()
