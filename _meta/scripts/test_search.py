#!/usr/bin/env python3
"""Unit tests for ``wiki_cli.py search`` (word-boundary, alias phrase boost,
all-terms bonus, rarity weighting, --include-raw, JSON shape).

Run from the vault root with either
``.venv/bin/python _meta/scripts/test_search.py`` or
``.venv/bin/python -m unittest _meta/scripts/test_search.py``.
"""

from __future__ import annotations

import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

import wiki_cli


def write_page(root: Path, relative: str, title: str, body: str, aliases: list[str] | None = None) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f'title: "{title}"']
    if aliases:
        lines.append("aliases:")
        lines.extend(f'  - "{alias}"' for alias in aliases)
    lines.extend(['note_type: "concept"', "---", "", f"# {title}", "", body, ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def paths_of(result: dict[str, object]) -> list[str]:
    return [str(item["path"]) for item in result["results"]]  # type: ignore[index]


class SearchTermsTest(unittest.TestCase):
    def test_keeps_two_letter_acronyms_and_drops_function_words(self) -> None:
        self.assertEqual(wiki_cli.search_terms("the FE model of the CL frame"), ["fe", "model", "cl", "frame"])

    def test_lowercases_splits_punctuation_and_dedupes(self) -> None:
        self.assertEqual(wiki_cli.search_terms("T.BULKHEAD sheet frame, sheet"), ["bulkhead", "sheet", "frame"])
        self.assertEqual(wiki_cli.search_terms("Physics-Informed"), ["physics", "informed"])

    def test_all_stopword_query_still_runs(self) -> None:
        self.assertEqual(wiki_cli.search_terms("the of"), ["the", "of"])


class TermRegexTest(unittest.TestCase):
    def matches(self, term: str, text: str) -> int:
        return len(re.findall(wiki_cli.term_regex(term), text.lower()))

    def test_word_boundaries_reject_substrings(self) -> None:
        self.assertEqual(self.matches("gate", "the surrogate model has a gate and two gates"), 2)
        self.assertEqual(self.matches("net", "meshgraphnet uses a net scantling"), 1)
        self.assertEqual(self.matches("fe", "the FE model; fees are not FE; iron is Fe"), 3)

    def test_separators_underscore_dot_hyphen(self) -> None:
        self.assertEqual(self.matches("v17", "SHIPYARD_TANK_V17.FCStd"), 1)
        self.assertEqual(self.matches("shipyard", "SHIPYARD_TANK_V17"), 1)
        self.assertEqual(self.matches("bulkhead", "T.BULKHEAD SECTION"), 1)
        self.assertEqual(self.matches("informed", "physics-informed neural network"), 1)

    def test_light_plural_stem_both_directions(self) -> None:
        self.assertEqual(self.matches("slot", "one slot, two slots, slotted"), 2)
        self.assertEqual(self.matches("slots", "one slot, two slots"), 2)
        self.assertEqual(self.matches("mesh", "a mesh and meshes; meshing"), 2)
        self.assertEqual(self.matches("taxonomies", "taxonomy of taxonomies"), 2)
        self.assertEqual(self.matches("class", "class rules for classes"), 2)
        self.assertEqual(self.matches("values", "one value, all values"), 2)


class SearchWikiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for relative in ("wiki/sources", "wiki/concepts", "wiki/projects", "wiki/derived", "raw"):
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki/INDEX.md").write_text("# Index\n\nfiller page about ships.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_word_boundary_kills_substring_false_positive(self) -> None:
        write_page(
            self.root,
            "wiki/concepts/surrogate-models.md",
            "Surrogate Models",
            " ".join(["surrogate models replace solvers."] * 40),
        )
        write_page(
            self.root,
            "wiki/derived/lessons.md",
            "Iteration lessons",
            "The recall gate checks that every drawn entity got a disposition.",
        )
        result = wiki_cli.search_wiki(self.root, "recall gate", limit=5)
        self.assertEqual(paths_of(result), ["wiki/derived/lessons.md"])
        self.assertIn("recall gate", result["results"][0]["snippet"].lower())  # type: ignore[index]

    def test_alias_phrase_boost_and_title_phrase_boost(self) -> None:
        write_page(
            self.root,
            "wiki/sources/long-source.md",
            "A long source page",
            "visual pair review appears here. " * 30,
        )
        write_page(
            self.root,
            "wiki/concepts/harness.md",
            "Review Harness",
            "visual pair review appears here once.",
            aliases=["visual pair review", "pair probe"],
        )
        write_page(
            self.root,
            "wiki/concepts/exact-title.md",
            "Recall Gate",
            "Body text without the query words.",
        )
        result = wiki_cli.search_wiki(self.root, "visual pair review", limit=5)
        self.assertEqual(paths_of(result)[0], "wiki/concepts/harness.md")
        scores = {item["path"]: item["score"] for item in result["results"]}  # type: ignore[index]
        self.assertGreater(scores["wiki/concepts/harness.md"], scores["wiki/sources/long-source.md"])
        # The bonus is exactly SEARCH_PHRASE_BONUS when every term matches.
        terms = wiki_cli.search_terms("visual pair review")
        patterns = wiki_cli.search_patterns(terms)
        harness = wiki_cli.search_document(self.root, self.root / "wiki/concepts/harness.md")
        counts = wiki_cli.search_term_counts(harness["fields"], patterns)  # type: ignore[arg-type]
        rarity = {term: 1.0 for term in terms}
        with_bonus, matched = wiki_cli.search_score(counts, rarity, phrase_match=True)
        without_bonus, _ = wiki_cli.search_score(counts, rarity, phrase_match=False)
        self.assertEqual(matched, 3)
        self.assertAlmostEqual(with_bonus - without_bonus, wiki_cli.SEARCH_PHRASE_BONUS)
        # A partial query is not the whole phrase, so no bonus applies to it.
        partial = wiki_cli.search_wiki(self.root, "visual pair", limit=5)
        partial_scores = {item["path"]: item["score"] for item in partial["results"]}  # type: ignore[index]
        self.assertLess(partial_scores["wiki/concepts/harness.md"], scores["wiki/concepts/harness.md"])
        # Title equality (case-insensitive) earns the same bonus.
        title_hit = wiki_cli.search_wiki(self.root, "RECALL GATE", limit=5)
        self.assertEqual(paths_of(title_hit)[0], "wiki/concepts/exact-title.md")

    def test_all_terms_bonus_prefers_documents_holding_every_term(self) -> None:
        write_page(
            self.root,
            "wiki/sources/neural-only.md",
            "Neural things",
            " ".join(["neural"] * 60),
        )
        write_page(
            self.root,
            "wiki/sources/both-terms.md",
            "Operator notes",
            "a neural operator maps functions to functions.",
        )
        result = wiki_cli.search_wiki(self.root, "neural operator", limit=5)
        self.assertEqual(paths_of(result)[0], "wiki/sources/both-terms.md")

    def test_rarity_weights_rare_terms_higher(self) -> None:
        for index in range(6):
            write_page(self.root, f"wiki/sources/common-{index}.md", f"Common {index}", "mesh mesh mesh")
        write_page(self.root, "wiki/sources/rare.md", "Rare page", "scantling scantling scantling")
        terms = ["mesh", "scantling"]
        patterns = wiki_cli.search_patterns(terms)
        docs = [wiki_cli.search_document(self.root, path) for path in wiki_cli.wiki_documents(self.root)]
        counts = [wiki_cli.search_term_counts(doc["fields"], patterns) for doc in docs]  # type: ignore[arg-type]
        rarity = wiki_cli.search_rarity(counts, terms)
        self.assertGreater(rarity["scantling"], rarity["mesh"])
        result = wiki_cli.search_wiki(self.root, "mesh scantling", limit=10)
        self.assertEqual(paths_of(result)[0], "wiki/sources/rare.md")

    def test_terms_absent_from_corpus_do_not_penalize(self) -> None:
        write_page(self.root, "wiki/concepts/frames.md", "Frames", "a web frame and a frame spacing.")
        result = wiki_cli.search_wiki(self.root, "frame zzqqxx", limit=5)
        self.assertEqual(paths_of(result), ["wiki/concepts/frames.md"])

    def test_body_count_cap_stops_length_from_winning(self) -> None:
        write_page(self.root, "wiki/sources/long.md", "Long page", " ".join(["seam"] * 500))
        write_page(
            self.root,
            "wiki/concepts/seam-symbols.md",
            "Seam Symbols",
            "seam symbol legend",
            aliases=["seam symbol"],
        )
        result = wiki_cli.search_wiki(self.root, "seam", limit=5)
        scores = {item["path"]: item["score"] for item in result["results"]}  # type: ignore[index]
        # 500 body hits count as SEARCH_FIELD_CAPS["body"] (20); df=2 of 3 documents.
        expected_long = wiki_cli.SEARCH_FIELD_CAPS["body"] * math.log(1 + 3 / 2)
        self.assertAlmostEqual(scores["wiki/sources/long.md"], expected_long, places=2)
        # title (10) + alias (8) + heading (3) + one body hit (1) beats the capped long page.
        self.assertEqual(paths_of(result)[0], "wiki/concepts/seam-symbols.md")

    def test_include_raw_flag(self) -> None:
        (self.root / "raw/notes").mkdir(parents=True)
        (self.root / "raw/notes/scratch.md").write_text("# Scratch\n\nzebrastripe idea.\n", encoding="utf-8")
        self.assertEqual(paths_of(wiki_cli.search_wiki(self.root, "zebrastripe", limit=5)), [])
        with_raw = wiki_cli.search_wiki(self.root, "zebrastripe", limit=5, include_raw=True)
        self.assertEqual(paths_of(with_raw), ["raw/notes/scratch.md"])

    def test_json_shape_and_limit(self) -> None:
        for index in range(4):
            write_page(self.root, f"wiki/sources/p{index}.md", f"Page {index}", "bulkhead plating")
        result = wiki_cli.search_wiki(self.root, "T.BULKHEAD plating", limit=2)
        self.assertEqual(set(result), {"query", "results"})
        self.assertEqual(result["query"], "T.BULKHEAD plating")
        self.assertEqual(len(result["results"]), 2)  # type: ignore[arg-type]
        for item in result["results"]:  # type: ignore[union-attr]
            self.assertEqual(set(item), {"path", "title", "score", "snippet"})
            self.assertGreater(item["score"], 0)

    def test_cli_include_raw_is_wired(self) -> None:
        (self.root / "raw/notes").mkdir(parents=True)
        (self.root / "raw/notes/scratch.md").write_text("# Scratch\n\nzebrastripe idea.\n", encoding="utf-8")
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = wiki_cli.main(["search", "--root", str(self.root), "--include-raw", "zebrastripe"])
        self.assertEqual(code, 0)
        self.assertIn("raw/notes/scratch.md", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
