"""Tests for check.py and obsidian_checks.py. Run from this folder: python3 -m unittest test_check -v"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check  # noqa: E402
import obsidian_checks  # noqa: E402


def run_check(args: list[str]) -> tuple[int, str]:
    """Run check.main from this folder; return (exit code, captured stdout).

    Fixture paths are relative to this folder, for example 'testdata/github'.
    The previous working folder is restored afterwards.
    """
    previous = os.getcwd()
    out = io.StringIO()
    try:
        os.chdir(HERE)
        with contextlib.redirect_stdout(out):
            code = check.main(["check.py", *args])
    finally:
        os.chdir(previous)
    return code, out.getvalue()


class TestGithubMode(unittest.TestCase):
    maxDiff = None

    def test_output_is_unchanged(self):
        expected = (HERE / "testdata" / "github" / "expected.txt").read_text(encoding="utf-8")
        code, output = run_check(["testdata/github"])
        self.assertEqual(output, expected)
        self.assertEqual(code, 1)


class TestPrimitives(unittest.TestCase):
    maxDiff = None

    FENCED = ["> ```kql", "> T | take 1", "> ```", "after"]

    def test_unquote_depth(self):
        self.assertEqual(obsidian_checks.unquote("> > [!example]- Solution"), (2, "[!example]- Solution"))

    def test_fence_inside_callout_is_masked(self):
        self.assertEqual(obsidian_checks.fence_mask(self.FENCED), [True, True, True, False])

    def test_fence_in_nested_callout_is_masked(self):
        nested = ["> > " + line[2:] if line.startswith("> ") else line for line in self.FENCED]
        self.assertEqual(nested[0], "> > ```kql")
        self.assertEqual(obsidian_checks.fence_mask(nested), [True, True, True, False])

    def test_plugin_mask_ignores_quoted_fence(self):
        self.assertEqual(obsidian_checks.plugin_fence_mask(self.FENCED), [False, False, False, False])

    def test_nested_callouts(self):
        lines = [
            "> [!example]- Exercise",
            "> Write the query.",
            "> > [!example]- Solution",
            "> > The answer.",
            "after",
        ]
        found = obsidian_checks.callouts(lines)
        self.assertEqual([c.depth for c in found], [1, 2])
        self.assertEqual([c.fold for c in found], ["-", "-"])
        self.assertEqual([(c.start, c.end) for c in found], [(1, 4), (3, 4)])
        self.assertEqual(found[0].body, ["Write the query.", "[!example]- Solution", "The answer."])
        self.assertEqual(found[1].title, "Solution")

    def test_callout_fold_values(self):
        lines = ["> [!question] A", "", "> [!question]+ B", "", "> [!question]- C"]
        found = obsidian_checks.callouts(lines)
        self.assertEqual([c.fold for c in found], ["", "+", "-"])
        self.assertEqual([c.kind for c in found], ["question"] * 3)

    def test_header_inside_fence_is_not_a_callout(self):
        lines = ["> [!example] Demo", "> ```md", "> [!note] inside code", "> ```"]
        found = obsidian_checks.callouts(lines)
        self.assertEqual([(c.start, c.title) for c in found], [(1, "Demo")])
        self.assertEqual(found[0].end, 4)

    def test_header_continuing_a_quote_is_body_text(self):
        back_to_back = obsidian_checks.callouts(["> [!a] A", "> [!b] B", "> x"])
        self.assertEqual([(c.start, c.end, c.title) for c in back_to_back], [(1, 3, "A")])
        self.assertEqual(back_to_back[0].body, ["[!b] B", "x"])
        empty_line_between = obsidian_checks.callouts(["> [!a] A", ">", "> [!b] B"])
        self.assertEqual([(c.start, c.end, c.title) for c in empty_line_between], [(1, 3, "A")])
        self.assertEqual(empty_line_between[0].body, ["", "[!b] B"])

    def test_crlf_lines(self):
        found = obsidian_checks.callouts(["> [!question] Quick check\r", "> Body\r"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].title, "Quick check")
        self.assertEqual(found[0].body, ["Body"])

    def test_card_sections(self):
        lines = [
            "# Real-time intelligence",
            "## Eventstream (card)",
            "```python",
            "# PySpark comment, not a heading",
            "```",
            "## Eventhouse (card)",
            "Body text.",
            "trailing line",
        ]
        self.assertEqual(
            obsidian_checks.card_sections(lines),
            [(2, 5, "Eventstream (card)"), (6, 8, "Eventhouse (card)")],
        )


OBSIDIAN = HERE / "testdata" / "obsidian"


class FakeReport:
    """Records findings as (line, msg), so tests can count them without printing."""

    def __init__(self):
        self.fails = []
        self.warns = []

    def fail(self, path, line, msg):
        self.fails.append((line, msg))

    def warn(self, path, line, msg):
        self.warns.append((line, msg))


def check_lines(lines: list[str]) -> FakeReport:
    rep = FakeReport()
    obsidian_checks.check_note("note.md", lines, rep, obsidian_checks.Separators())
    return rep


class TestObsidianRules(unittest.TestCase):
    """Each test checks the fixture testdata/obsidian/<test name>.md."""

    maxDiff = None

    def check_fixture(self, fails: int, text: str | None = None, warns: int | None = None) -> FakeReport:
        """Assert the FAIL count of this test's fixture and, if given, a substring of the first FAIL.

        The WARN count is checked when warns is given. A fixture that expects
        0 FAIL must also give 0 WARN, unless warns says otherwise.
        """
        path = OBSIDIAN / f"{self._testMethodName}.md"
        lines = path.read_text(encoding="utf-8").split("\n")
        rep = check_lines(lines)
        self.assertEqual(len(rep.fails), fails, rep.fails)
        if warns is None and fails == 0:
            warns = 0
        if warns is not None:
            self.assertEqual(len(rep.warns), warns, rep.warns)
        if text is not None:
            self.assertIn(text, rep.fails[0][1])
        return rep

    def test_details_tag_fails(self):
        self.check_fixture(1, "details")

    def test_open_question_callout_fails(self):
        self.check_fixture(1, "not collapsed")

    def test_plus_fold_fails(self):
        self.check_fixture(1, "not collapsed")

    def test_solution_callout_must_fold(self):
        self.check_fixture(1, "not collapsed")

    def test_empty_answer_fails(self):
        self.check_fixture(1, "empty")

    def test_good_note_passes(self):
        self.check_fixture(0)

    def test_bad_trigger_line_fails(self):
        self.check_fixture(1, "trigger")

    def test_multiline_card_passes(self):
        self.check_fixture(0)

    def test_reversed_multiline_card_passes(self):
        self.check_fixture(0)

    def test_multiline_card_without_question_fails(self):
        rep = self.check_fixture(1, "incomplete multi-line trigger")
        self.assertEqual(rep.fails[0][0], 5)

    def test_multiline_card_without_answer_fails(self):
        self.check_fixture(1, "trigger")

    def test_separator_in_card_table_row_fails(self):
        self.check_fixture(1, "in this table line")

    def test_non_sr_comment_fails(self):
        rep = self.check_fixture(1, "comment")
        self.assertIn("the plugin can skip the next line", rep.fails[0][1])

    def test_quick_check_question_is_visible(self):
        self.check_fixture(1, "visible question")

    def test_code_completion_quick_check_passes(self):
        self.check_fixture(0)

    def test_multiline_scenario_quick_check_passes(self):
        self.check_fixture(0)

    def test_mock_question_label_passes(self):
        self.check_fixture(0)

    def test_options_without_label_pass(self):
        self.check_fixture(0)

    def test_question_label_without_options_passes(self):
        self.check_fixture(0)

    def test_table_and_sr_comment_are_not_triggers(self):
        self.check_fixture(0)

    def test_separator_in_quoted_fence_fails(self):
        self.check_fixture(1, "outside a card section")

    def test_separator_in_column0_fence_passes(self):
        self.check_fixture(0)

    def test_separator_in_inline_code_passes(self):
        self.check_fixture(0)

    def test_highlight_fails(self):
        self.check_fixture(1, "highlight")

    def test_bare_question_mark_line_fails(self):
        self.check_fixture(1, "only")

    def test_card_heading_with_colon_fails(self):
        self.check_fixture(1, "link")

    def test_answer_outside_callout_fails(self):
        self.check_fixture(1, "outside a callout")

    def test_answer_skew_counts_callout_answers(self):
        self.check_fixture(1, "skew")

    def test_answer_lean_warns(self):
        rep = self.check_fixture(0, warns=1)
        self.assertIn("answer lean", rep.warns[0][1])

    def test_merged_quick_check_fails(self):
        self.check_fixture(1, "continues the quote above")

    def test_unnested_solution_fails(self):
        self.check_fixture(1, "continues the quote above")

    def test_callout_header_after_extra_spaces(self):
        found = obsidian_checks.callouts([">  [!question] Answer", ">  Eventstream."])
        self.assertEqual([(c.kind, c.fold, c.title) for c in found], [("question", "", "Answer")])
        unfolded = check_lines(["> **Quick check:** Which item routes events?", "", ">  [!question] Answer", ">  Eventstream."])
        self.assertEqual(len(unfolded.fails), 1, unfolded.fails)
        self.assertIn("not collapsed", unfolded.fails[0][1])
        merged = check_lines(["> **Quick check:** Which item routes events?", ">  [!question]- Answer", ">  Eventstream."])
        self.assertEqual(len(merged.fails), 1, merged.fails)
        self.assertIn("continues the quote above", merged.fails[0][1])

    def test_inline_code_before_card_separator_fails(self):
        self.check_fixture(1, "skips the line")
        code_after = check_lines(["## One-line card (card)", "Which form makes a one-line card;;`question;;answer`"])
        self.assertEqual(code_after.fails, [])
        reversed_in_code = check_lines(["## One-line card (card)", "The form `a;;;b` makes which card;;A reversed card"])
        self.assertEqual(len(reversed_in_code.fails), 1, reversed_in_code.fails)
        self.assertIn("skips the line", reversed_in_code.fails[0][1])

    def test_separator_in_multiline_card_fails(self):
        self.check_fixture(1, "becomes a one-line card")
        in_code = check_lines(["## Eventstream (card)", "Which item routes", "the `a;;b` stream?", "?", "Eventstream"])
        self.assertEqual(in_code.fails, [])

    def test_card_separator_advice_fits_the_line(self):
        lines = ["## Eventstream (card)", "### a;;b", "> ```", "> x;;y", "> ```"]
        fails = check_lines(lines).fails
        self.assertEqual([line for line, _ in fails], [2, 4], fails)
        self.assertIn("remove it from the heading", fails[0][1])
        self.assertIn("column-0 fence", fails[1][1])

    def test_bom_and_crlf_note_passes(self):
        text = (OBSIDIAN / "test_good_note_passes.md").read_text(encoding="utf-8")
        lines = ("﻿" + "\r\n".join(text.split("\n"))).split("\n")
        self.assertTrue(lines[0].startswith("﻿"))
        self.assertTrue(lines[0].endswith("\r"))
        self.assertEqual(check_lines(lines).fails, [])


LINKS = OBSIDIAN / "links"
TARGET = LINKS / "dp700-10-eventstream.md"


def check_obsidian_file(path: pathlib.Path, index=None) -> FakeReport:
    rep = FakeReport()
    check.check_file(path, rep, target="obsidian", index=index)
    return rep


def check_link_lines(lines: list[str]) -> FakeReport:
    """Run only the link rules over lines, against an index of the target note."""
    rep = FakeReport()
    obsidian_checks.check_links(LINKS / "note.md", lines, rep, obsidian_checks.build_index([TARGET]))
    return rep


class TestLinks(unittest.TestCase):
    """Each fixture test checks testdata/obsidian/links/<test name>.md in Obsidian mode.

    The index holds the fixture and links/dp700-10-eventstream.md.
    """

    maxDiff = None

    def check_fixture(self, fails: int, text: str | None = None) -> FakeReport:
        path = LINKS / f"{self._testMethodName}.md"
        rep = check_obsidian_file(path, obsidian_checks.build_index([TARGET, path]))
        self.assertEqual(len(rep.fails), fails, rep.fails)
        self.assertEqual(rep.warns, [])
        if text is not None:
            self.assertIn(text, rep.fails[0][1])
        return rep

    def test_missing_note_fails(self):
        rep = self.check_fixture(1, "no such note")
        self.assertIn("[[dp700-99-nothing]]", rep.fails[0][1])

    def test_missing_heading_fails(self):
        rep = self.check_fixture(1, "no such heading")
        self.assertIn("![[dp700-10-eventstream#Eventhouse (card)]]", rep.fails[0][1])

    def test_alias_and_case_resolve(self):
        self.check_fixture(0)

    def test_attachment_embed_is_skipped(self):
        self.check_fixture(0)

    def test_odd_fence_inside_callout_fails(self):
        self.check_fixture(1, "odd number")

    def test_same_note_heading_link_resolves(self):
        self.check_fixture(0)

    def test_index_defaults_to_the_note_itself(self):
        rep = check_obsidian_file(LINKS / f"{self._testMethodName}.md")
        self.assertEqual(len(rep.fails), 1, rep.fails)
        self.assertIn("no such note", rep.fails[0][1])
        self.assertIn("[[dp700-10-eventstream]]", rep.fails[0][1])

    def test_build_index(self):
        index = obsidian_checks.build_index([TARGET])
        self.assertEqual(list(index), ["dp700-10-eventstream"])
        headings = index["dp700-10-eventstream"]
        self.assertIn("eventstream (card)", headings)
        self.assertIn("§1 spaced out heading", headings)
        self.assertNotIn("hidden heading", headings)
        self.assertNotIn("quoted heading", headings)

    def test_first_of_two_same_stems_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = pathlib.Path(tmp) / "a" / "Note.md"
            second = pathlib.Path(tmp) / "b" / "note.md"
            for path, heading in ((first, "# From a"), (second, "# From b")):
                path.parent.mkdir()
                path.write_text(heading + "\n", encoding="utf-8")
            index = obsidian_checks.build_index([second, first])
        self.assertEqual(index, {"note": {"from a"}})

    def test_folder_path_md_suffix_and_table_alias_resolve(self):
        lines = [
            "[[notes/dp700-10-eventstream.md#Eventstream (card)]]",
            "[[DP700-10-EVENTSTREAM#§1  Spaced   out heading]]",
            "| [[dp700-10-eventstream#Eventstream (card)\\|card]] | x |",
        ]
        self.assertEqual(check_link_lines(lines).fails, [])

    def test_urls_and_block_references(self):
        lines = [
            "[[https://learn.microsoft.com/fabric]]",
            "[[dp700-10-eventstream#^abc123]]",
            "[[#^abc123]]",
            "![[clip.mp4]] and ![[slides.pdf#page=2]]",
            "[[dp700-99-nothing#^abc123]]",
        ]
        fails = check_link_lines(lines).fails
        self.assertEqual([line for line, _ in fails], [5], fails)
        self.assertIn("no such note", fails[0][1])

    def test_links_in_code_are_ignored_and_callouts_count(self):
        lines = [
            "```md",
            "[[dp700-99-nothing]]",
            "```",
            "> ```md",
            "> [[dp700-99-nothing]]",
            "> ```",
            "Write `[[dp700-99-nothing]]` for a link.",
            "> [!note] See also",
            "> > [[dp700-10-eventstream#Hidden heading]]",
        ]
        fails = check_link_lines(lines).fails
        self.assertEqual([line for line, _ in fails], [9], fails)
        self.assertIn("no such heading", fails[0][1])

    def test_one_fail_per_broken_link(self):
        fails = check_link_lines(["[[dp700-99-nothing]] then [[dp700-10-eventstream#Nope]]"]).fails
        self.assertEqual(len(fails), 2, fails)
        self.assertIn("[[dp700-99-nothing]]", fails[0][1])
        self.assertIn("[[dp700-10-eventstream#Nope]]", fails[1][1])


class TestTargetOption(unittest.TestCase):
    maxDiff = None

    def test_obsidian_fixture_folder(self):
        code, output = run_check(["--target", "obsidian", "testdata/obsidian/pilot"])
        self.assertIn("2 files checked: 0 FAIL, 0 WARN", output)
        self.assertEqual(code, 0, output)
        _, github_output = run_check(["testdata/obsidian/pilot"])
        self.assertIn("stacked lines", github_output)  # so the 0 WARN above means the check is off

    def test_default_target_is_github(self):
        expected = (HERE / "testdata" / "github" / "expected.txt").read_text(encoding="utf-8")
        self.assertEqual(run_check(["testdata/github"])[1], expected)
        self.assertEqual(run_check(["--target", "github", "testdata/github"])[1], expected)

    def test_obsidian_mode_runs_kept_checks(self):
        code, output = run_check(["--target", "obsidian", "testdata/obsidian/kept/glossary_and_conflict.md"])
        self.assertIn("1 files checked: 2 FAIL, 0 WARN", output)
        self.assertIn("glossary term 'Watermark' never appears in the body", output)
        self.assertIn("merge-conflict marker", output)
        self.assertEqual(code, 1)

    def test_card_separator_option(self):
        path = "testdata/obsidian/options/custom_separator.md"
        code, output = run_check(["--target", "obsidian", "--card-separator", "::", "--reversed-separator", ":::", path])
        self.assertIn("1 files checked: 0 FAIL, 0 WARN", output)
        self.assertEqual(code, 0, output)
        code, output = run_check(["--target", "obsidian", path])
        self.assertIn("1 files checked: 2 FAIL, 0 WARN", output)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
