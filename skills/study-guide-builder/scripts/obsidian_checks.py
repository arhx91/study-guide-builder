"""Parsing primitives for checking study notes written for Obsidian.

Obsidian notes put exercises and answers in callouts (`> [!example]- Solution`),
so code fences and headings can sit behind one or more `>` markers. These
helpers see through the quote markers. check.py builds its Obsidian rules on
them, so this module must not import check.
"""
from __future__ import annotations

import pathlib
import re
from collections import Counter
from dataclasses import dataclass

CALLOUT_RE = re.compile(r"^\[!(\w+)\]([+-]?)\s*(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s")
FENCE_MARKERS = ("```", "~~~")
CARD_SUFFIX = " (card)"

# Copied from check.py, because this module must not import check.
ANSWER_RE = re.compile(r"\*\*Answer: ([A-D])\*\*")
OPTION_RE = re.compile(r"^\s*(?:[-*]\s+)?\(?[A-D][.)]\s+\S")

ANSWER_MARK = "**Answer:"
ANSWER_TITLES = ("answer", "solution")
QUICK_CHECK_LABEL = "**Quick check:**"
QUESTION_LABEL_RE = re.compile(r"\*\*Question \d+:\*\*")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
CODE_FILL = "\0"  # stands in for inline code: not blank, and part of no pattern below
SR_COMMENT_RE = re.compile(r"<!--SR:.*?-->")
SR_LINE_RE = re.compile(r"^<!--SR:.*-->$")
TRAILING_SR_RE = re.compile(r"\s*<!--SR:.*?-->\s*$")
HIGHLIGHT_RE = re.compile(r"==[^=\s](?:[^=]*[^=\s])?==")  # Obsidian: no space inside the marks
LINK_BREAKERS = ("#", "|", "^", ":", "%%", "[[", "]]")
BOM = "﻿"
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]\0]*)\]\]")  # \0 is CODE_FILL: a link may not run into inline code
ATTACHMENT_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")


@dataclass
class Callout:
    """One callout. Line numbers are 1-based; body holds the unquoted lines after the header."""

    start: int
    end: int
    depth: int
    kind: str
    fold: str
    title: str
    body: list[str]


def _clean(line: str) -> str:
    """Drop a trailing carriage return, so Windows line ends parse like Unix ones."""
    return line[:-1] if line.endswith("\r") else line


def unquote(line: str) -> tuple[int, str]:
    """Return the quote depth of a line and its text after all `>` markers.

    One space after each `>` belongs to the marker. A line without markers
    comes back unchanged, apart from a trailing carriage return.
    """
    text = _clean(line)
    depth = 0
    while True:
        rest = text.lstrip(" \t")
        if not rest.startswith(">"):
            return depth, text
        depth += 1
        text = rest[1:]
        if text.startswith(" "):
            text = text[1:]


def _callout_header(text: str) -> re.Match | None:
    """Match CALLOUT_RE on unquoted text, after any spaces that follow the marker space."""
    return CALLOUT_RE.match(text.lstrip(" "))


def _fence_marker(text: str) -> str | None:
    """The marker character a fence line uses, or None if the text is not a fence line."""
    for marker in FENCE_MARKERS:
        if text.startswith(marker):
            return marker[0]
    return None


def _fence_state(fence_texts: list[str | None]) -> tuple[list[bool], int, bool]:
    """Fence mask over candidate fence texts; None means the line cannot be a fence.

    A fence closes only on a line with the marker character it opened with.
    Fence lines themselves are True. Also returns how many lines opened or
    closed a fence, and whether a fence is still open after the last line.
    """
    mask = []
    open_marker = None
    fence_lines = 0
    for text in fence_texts:
        marker = _fence_marker(text) if text is not None else None
        if open_marker is None and marker is not None:
            open_marker = marker
            fence_lines += 1
            mask.append(True)
        elif open_marker is not None and marker == open_marker:
            open_marker = None
            fence_lines += 1
            mask.append(True)
        else:
            mask.append(open_marker is not None)
    return mask, fence_lines, open_marker is not None


def _mask(fence_texts: list[str | None]) -> list[bool]:
    return _fence_state(fence_texts)[0]


def _fence_texts(lines: list[str]) -> list[str]:
    """Each line as fence_mask sees it: after the quote markers and leading space."""
    return [unquote(line)[1].lstrip() for line in lines]


def fence_mask(lines: list[str]) -> list[bool]:
    """True for lines inside a code fence, including the fence lines, at any quote depth.

    Like check.fence_mask, a fence line may be indented.
    """
    return _mask(_fence_texts(lines))


def plugin_fence_mask(lines: list[str]) -> list[bool]:
    """True only inside fences that start at column 0, the fences the plugin skips.

    A fence behind `>` markers or indentation does not count here.
    """
    return _mask([_clean(line) for line in lines])


def callouts(lines: list[str]) -> list[Callout]:
    """Every callout in the lines, nested ones included, in order of their header line.

    The body runs while the quote depth stays at or above the callout depth,
    so a nested callout's lines are also part of the outer body. A header
    line inside a code fence is code, not a callout. A header must open its
    quote level: a `[!type]` line that continues a quote at the same depth
    is body text.
    """
    quoted = [unquote(line) for line in lines]
    mask = fence_mask(lines)
    found = []
    for i, (depth, text) in enumerate(quoted):
        if depth < 1 or mask[i]:
            continue
        if i > 0 and quoted[i - 1][0] >= depth:
            continue
        match = _callout_header(text)
        if not match:
            continue
        body = []
        for body_depth, body_text in quoted[i + 1:]:
            if body_depth < depth:
                break
            body.append(body_text)
        start = i + 1
        found.append(Callout(
            start=start,
            end=start + len(body),
            depth=depth,
            kind=match.group(1),
            fold=match.group(2),
            title=match.group(3).strip(),
            body=body,
        ))
    return found


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Line number, level and text of every heading.

    Headings are unquoted lines outside code fences, so a `#` comment in a
    PySpark block is not one.
    """
    mask = fence_mask(lines)
    headings = []
    for i, line in enumerate(lines):
        line = _clean(line)
        if mask[i] or unquote(line)[0] != 0:
            continue
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            headings.append((i + 1, level, line[level:].strip()))
    return headings


def card_sections(lines: list[str]) -> list[tuple[int, int, str]]:
    """Start line, end line and heading text of every heading that ends in ' (card)'.

    Headings are found as in _headings. A section ends on the line before
    the next heading of the same or a higher level, or at the end of the file.
    """
    headings = _headings(lines)
    sections = []
    for n, (start, level, text) in enumerate(headings):
        if not text.endswith(CARD_SUFFIX):
            continue
        end = len(lines)
        for next_start, next_level, _ in headings[n + 1:]:
            if next_level <= level:
                end = next_start - 1
                break
        sections.append((start, end, text))
    return sections


@dataclass
class Separators:
    """Card separators of the Spaced Repetition plugin, as the guide configures them."""

    single: str = ";;"
    reversed: str = ";;;"
    multi: str = "?"
    multi_reversed: str = "??"


@dataclass
class _Note:
    """One note, parsed once for all rules. Line numbers in the sets are 1-based."""

    path: object
    lines: list[str]
    fenced: list[bool]
    plugin_fenced: list[bool]
    callouts: list[Callout]
    sections: list[tuple[int, int, str]]
    callout_lines: set[int]
    card_lines: set[int]

    def text(self, n: int) -> str:
        """Line n with inline code replaced by CODE_FILL, so searches skip code spans."""
        return _hide_code(self.lines[n - 1])

    def numbers(self, mask: list[bool]) -> list[int]:
        """Line numbers that the mask leaves open."""
        return [n for n in range(1, len(self.lines) + 1) if not mask[n - 1]]


def _hide_code(text: str) -> str:
    """Replace each inline code span by CODE_FILL characters of the same length.

    Removing the span instead could join the text around it into a new
    separator ("a;`x`;b" would become "a;;b").
    """
    return INLINE_CODE_RE.sub(lambda m: CODE_FILL * len(m.group()), text)


def clean_lines(lines: list[str]) -> list[str]:
    """Lines without trailing carriage returns and without a leading BOM."""
    lines = [_clean(line) for line in lines]
    if lines and lines[0].startswith(BOM):
        lines[0] = lines[0][len(BOM):]
    return lines


def _parse(path, lines: list[str]) -> _Note:
    lines = clean_lines(lines)
    found = callouts(lines)
    sections = card_sections(lines)
    return _Note(
        path=path,
        lines=lines,
        fenced=fence_mask(lines),
        plugin_fenced=plugin_fence_mask(lines),
        callouts=found,
        sections=sections,
        callout_lines={n for c in found for n in range(c.start, c.end + 1)},
        card_lines={n for start, end, _ in sections for n in range(start, end + 1)},
    )


def check_note(path, lines: list[str], rep, seps: Separators) -> None:
    """Run every per-note Obsidian rule. rep needs fail(path, line, msg) and warn(path, line, msg)."""
    note = _parse(path, lines)
    _check_details(note, rep)
    _check_merged_callouts(note, rep)
    _check_collapsed(note, rep)
    _check_empty_answers(note, rep)
    _check_answer_outside_callout(note, rep)
    _check_answer_skew(note, rep)
    _check_visible_question(note, rep)
    _check_card_triggers(note, seps, rep)
    _check_card_code_separators(note, seps, rep)
    _check_multi_line_separators(note, seps, rep)
    _check_card_separators(note, seps, rep)
    _check_card_headings(note, rep)
    _check_stray_separators(note, seps, rep)
    _check_bare_markers(note, seps, rep)
    _check_highlights(note, rep)
    _check_comments(note, rep)


# Rule 1


def _check_details(note: _Note, rep) -> None:
    for n in note.numbers(note.fenced):
        if "<details" in note.text(n).lower():
            rep.fail(note.path, n, "<details> tag; Obsidian does not render Markdown inside it, use a folded callout")


# A callout header that continues the quote above it


def _check_merged_callouts(note: _Note, rep) -> None:
    """A [!type] line at the same or a lower depth than the line above is body text, not a callout."""
    quoted = [unquote(line) for line in note.lines]
    for n in note.numbers(note.fenced):
        depth, text = quoted[n - 1]
        match = _callout_header(text)
        if n == 1 or depth < 1 or not match:
            continue
        if quoted[n - 2][0] >= depth:
            rep.fail(note.path, n, f"[!{match.group(1)}] line continues the quote above, so Obsidian shows it as text. Put a blank line above it")


# Rules 2 and 3: answer regions


def _own_lines(note: _Note, c: Callout) -> list[int]:
    """Body lines of a callout that do not belong to a callout nested in it."""
    nested = {
        n
        for d in note.callouts
        if c.start < d.start <= c.end
        for n in range(d.start, d.end + 1)
    }
    return [n for n in range(c.start + 1, c.end + 1) if n not in nested]


def _is_answer_region(note: _Note, c: Callout) -> bool:
    if c.kind.lower() == "question" or c.title.lower().startswith(ANSWER_TITLES):
        return True
    return any(
        ANSWER_MARK in _hide_code(unquote(note.lines[n - 1])[1])
        for n in _own_lines(note, c)
        if not note.fenced[n - 1]
    )


def _answer_regions(note: _Note) -> list[Callout]:
    return [c for c in note.callouts if _is_answer_region(note, c)]


def _check_collapsed(note: _Note, rep) -> None:
    for c in _answer_regions(note):
        if c.fold != "-":
            rep.fail(note.path, c.start, f"answer callout [!{c.kind}]{c.fold} is not collapsed; write [!{c.kind}]- so the answer folds")


def _check_empty_answers(note: _Note, rep) -> None:
    for c in _answer_regions(note):
        if not any(line.strip() for line in c.body):
            rep.fail(note.path, c.start, f"answer callout [!{c.kind}] is empty; put the answer in its body")


# Answer lines and their letter distribution


def _check_answer_outside_callout(note: _Note, rep) -> None:
    for n in note.numbers(note.fenced):
        if n not in note.callout_lines and ANSWER_RE.search(note.text(n)):
            rep.fail(note.path, n, "**Answer: X** line outside a callout; put it in a folded [!question]- Answer callout")


def _check_answer_skew(note: _Note, rep) -> None:
    """Same thresholds and messages as check.check_multiple_choice."""
    answers = []
    for n in note.numbers(note.fenced):
        m = ANSWER_RE.search(note.text(n))
        if m:
            answers.append(m.group(1))
    if len(answers) < 8:
        return
    counts = Counter(answers)
    letter, top = counts.most_common(1)[0]
    share = top / len(answers)
    spread = " ".join(f"{k}={counts.get(k, 0)}" for k in "ABCD")
    if share > 0.5:
        rep.fail(note.path, 0, f"answer skew: {letter} is {share:.0%} of {len(answers)} answers ({spread})")
    elif share > 0.4:
        rep.warn(note.path, 0, f"answer lean: {letter} is {share:.0%} of {len(answers)} answers ({spread})")


# Rule 10: the question stays visible


def _skip_blank_up(note: _Note, n: int) -> int:
    while n >= 1 and not note.lines[n - 1].strip():
        n -= 1
    return n


def _run_up(note: _Note, n: int) -> list[int]:
    """The run of non-blank lines that ends at line n, top first.

    It stops at a blank line or a callout line. A fenced line counts as
    non-blank, so a blank line inside a code block does not split the block.
    """
    run = []
    while n >= 1 and n not in note.callout_lines and (note.lines[n - 1].strip() or note.fenced[n - 1]):
        run.append(n)
        n -= 1
    return run[::-1]


def _visible_block(note: _Note, c: Callout) -> list[int]:
    """Line numbers of the visible block directly above a callout, top first."""
    block = _run_up(note, _skip_blank_up(note, c.start - 1))
    if block:
        first = note.lines[block[0] - 1]
        if note.fenced[block[0] - 1] and unquote(first)[0] == 0 and _fence_marker(first.lstrip()):
            block = _run_up(note, _skip_blank_up(note, block[0] - 1)) + block
    return block


def _shows_question(note: _Note, block: list[int]) -> bool:
    visible = [n for n in block if not note.fenced[n - 1]]
    texts = [unquote(note.lines[n - 1])[1] for n in visible]
    if any(QUICK_CHECK_LABEL in t or QUESTION_LABEL_RE.search(t) for t in texts):
        return True
    return bool(visible) and visible[-1] == block[-1] and bool(OPTION_RE.match(texts[-1]))


def _check_visible_question(note: _Note, rep) -> None:
    for c in note.callouts:
        if c.kind.lower() == "question" and not _shows_question(note, _visible_block(note, c)):
            rep.fail(note.path, c.start, "[!question] callout has no visible question above it; put a > **Quick check:** or > **Question N:** line there")


# Rules 4, 4b and 8: card sections


def _card_line_kind(note: _Note, n: int) -> str:
    """One of: blank, code, heading, table, sr, trigger."""
    line = note.lines[n - 1]
    s = line.strip()
    if note.fenced[n - 1]:
        return "code"
    if not s:
        return "blank"
    if unquote(line)[0] == 0 and HEADING_RE.match(line):
        return "heading"
    if s.startswith("|"):
        return "table"
    if SR_LINE_RE.match(s):
        return "sr"
    return "trigger"


def _trigger_text(note: _Note, n: int) -> str:
    """A trigger line without a trailing SR comment, with inline code hidden."""
    return _hide_code(TRAILING_SR_RE.sub("", note.lines[n - 1]))


def _is_one_line_card(text: str, seps: Separators) -> bool:
    """Test the reversed separator first, because ';;;' contains ';;'."""
    for sep in (seps.reversed, seps.single):
        if sep in text:
            left, right = text.split(sep, 1)
            return bool(left.strip() and right.strip())
    return False


def _trigger_runs(note: _Note) -> list[list[int]]:
    """Runs of trigger lines in the card sections. Any line that is not a trigger line ends a run."""
    runs = []
    for start, end, _ in note.sections:
        run = []
        for n in range(start + 1, end + 1):
            if _card_line_kind(note, n) == "trigger":
                run.append(n)
                continue
            if run:
                runs.append(run)
            run = []
        if run:
            runs.append(run)
    return runs


def _marker_index(note: _Note, run: list[int], seps: Separators) -> int | None:
    """Index in the run of the first line that is only ? or ??, or None."""
    for i, n in enumerate(run):
        if _trigger_text(note, n).strip() in (seps.multi, seps.multi_reversed):
            return i
    return None


def _check_card_triggers(note: _Note, seps: Separators, rep) -> None:
    """A run with a ? or ?? line is one multi-line card; otherwise each line is a one-line card."""
    for run in _trigger_runs(note):
        first = _marker_index(note, run, seps)
        if first is not None:
            if first == 0 or first == len(run) - 1:
                rep.fail(note.path, run[first], f"incomplete multi-line trigger; put question lines above the {seps.multi} line and answer lines below it")
            continue
        for n in run:
            if not _is_one_line_card(_trigger_text(note, n), seps):
                rep.fail(note.path, n, f"trigger line is not a card; write question{seps.single}answer, or move the text out of the card section")


def _raw_trigger(note: _Note, n: int) -> str:
    """A trigger line without a trailing SR comment, with inline code kept."""
    return TRAILING_SR_RE.sub("", note.lines[n - 1])


def _in_inline_code(text: str, i: int) -> bool:
    return _hide_code(text)[i] == CODE_FILL


def _one_line_cards(note: _Note, seps: Separators) -> list[int]:
    """Trigger lines that the checker reads as one-line cards: card lines in runs without a ? or ?? line."""
    return [
        n
        for run in _trigger_runs(note)
        if _marker_index(note, run, seps) is None
        for n in run
        if _is_one_line_card(_trigger_text(note, n), seps)
    ]


def _check_card_code_separators(note: _Note, seps: Separators, rep) -> None:
    """The plugin tests only the first occurrence of a separator for inline code (hasInlineMarker, parser.ts:62-72)."""
    for n in _one_line_cards(note, seps):
        raw = _raw_trigger(note, n)
        sep = _separator_in(_trigger_text(note, n), seps)
        if _in_inline_code(raw, raw.find(sep)):
            rep.fail(note.path, n, f"the first '{sep}' on this card line is in inline code, so the plugin skips the line; take '{sep}' out of the inline code")


def _plugin_separator(text: str, seps: Separators) -> str | None:
    """The separator that makes the plugin read a line as a one-line card, or None.

    Like hasInlineMarker (parser.ts:62-72), the reversed separator goes first,
    only the first occurrence of each separator counts, and an occurrence in
    inline code does not count.
    """
    for sep in (seps.reversed, seps.single):
        i = text.find(sep)
        if i != -1 and not _in_inline_code(text, i):
            return sep
    return None


def _check_multi_line_separators(note: _Note, seps: Separators, rep) -> None:
    """A separator in any line of a multi-line card makes that line a one-line card (parser.ts:148-157)."""
    for run in _trigger_runs(note):
        first = _marker_index(note, run, seps)
        if first is None or not 0 < first < len(run) - 1:
            continue  # no multi-line card, or an incomplete one that _check_card_triggers fails
        for n in run:
            sep = _plugin_separator(_raw_trigger(note, n), seps)
            if sep:
                rep.fail(note.path, n, f"'{sep}' in a line of a multi-line card becomes a one-line card, and the plugin drops the multi-line card; rewrite the line")


def _separator_in(text: str, seps: Separators) -> str | None:
    for sep in (seps.reversed, seps.single):
        if sep in text:
            return sep
    return None


SEPARATOR_ADVICE = {
    "heading": "remove it from the heading",
    "table": "move the trigger under the table, or rewrite the row",
    "code": "put the code in a column-0 fence, or rewrite the line",
}


def _check_card_separators(note: _Note, seps: Separators, rep) -> None:
    """Rule 4b: a separator in a non-trigger line that the plugin still reads."""
    for start, end, _ in note.sections:
        for n in range(start, end + 1):
            kind = _card_line_kind(note, n)
            if kind not in ("heading", "table", "code") or note.plugin_fenced[n - 1]:
                continue
            sep = _separator_in(note.text(n), seps)
            if sep:
                rep.fail(note.path, n, f"'{sep}' in this {kind} line becomes a card; {SEPARATOR_ADVICE[kind]}")


def _check_card_headings(note: _Note, rep) -> None:
    for start, _, text in note.sections:
        name = text[: -len(CARD_SUFFIX)]
        bad = [ch for ch in LINK_BREAKERS if ch in name]
        if bad:
            rep.fail(note.path, start, f"card heading has {' '.join(repr(ch) for ch in bad)}; it breaks the embed link, remove it")


# Rule 5: outside card sections, the plugin also reads quoted fences


def _plugin_lines(note: _Note) -> list[int]:
    """Lines outside card sections that the plugin reads: all but column-0 fences."""
    return [n for n in note.numbers(note.plugin_fenced) if n not in note.card_lines]


def _check_stray_separators(note: _Note, seps: Separators, rep) -> None:
    for n in _plugin_lines(note):
        sep = _separator_in(note.text(n), seps)
        if sep:
            rep.fail(note.path, n, f"'{sep}' outside a card section becomes a card; put it in inline code or a column-0 fence, or rewrite it")


def _check_bare_markers(note: _Note, seps: Separators, rep) -> None:
    for n in _plugin_lines(note):
        marker = unquote(note.text(n))[1].strip()
        if marker in (seps.multi, seps.multi_reversed):
            rep.fail(note.path, n, f"a line with only '{marker}' becomes a multi-line card; join it to the line above")


def _check_highlights(note: _Note, rep) -> None:
    for n in _plugin_lines(note):
        if HIGHLIGHT_RE.search(note.text(n)):
            rep.fail(note.path, n, "==highlight== can become a cloze card; use **bold**, or put spaces around == in code")


# Rule 9


def _check_comments(note: _Note, rep) -> None:
    for n in note.numbers(note.plugin_fenced):
        text = note.text(n)
        starts = [m.start() for m in re.finditer(re.escape("<!--"), text)]
        if any(not SR_COMMENT_RE.match(text, i) for i in starts):
            rep.fail(note.path, n, "HTML comment that is not an SR comment; the plugin can skip the next line, remove it")


# Folder rules: fences, the note index, and rules 6 and 7


def check_fences(path, lines: list[str], rep) -> None:
    """Fail once when a fence is still open at the end, at any quote depth.

    The count is the number of lines that open or close a fence, so it is
    odd whenever a block never closes. Same message as check.check_fences.
    """
    _, count, still_open = _fence_state(_fence_texts(clean_lines(lines)))
    if still_open:
        rep.fail(path, 0, f"odd number of code fences ({count}); a block never closes")


def _normalize_heading(text: str) -> str:
    """Lower case, with runs of white space collapsed to one space."""
    return " ".join(text.lower().split())


def _heading_set(lines: list[str]) -> set[str]:
    return {_normalize_heading(text) for _, _, text in _headings(clean_lines(lines))}


def build_index(files: list[pathlib.Path]) -> dict[str, set[str]]:
    """Map each note's lower-case file stem to its normalized heading texts.

    Obsidian resolves note names without case. When two files share a stem,
    the first in sorted order wins.
    """
    index: dict[str, set[str]] = {}
    for path in sorted(pathlib.Path(f) for f in files):
        key = path.stem.lower()
        if key in index:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        index[key] = _heading_set(text.split("\n"))
    return index


def _note_key(target: str) -> str | None:
    """The index key for a link target, or None for a URL or an attachment."""
    if "://" in target:
        return None
    name = target.split("/")[-1]
    if name.lower().endswith(".md"):
        return name[:-3].lower()
    if ATTACHMENT_RE.search(name):
        return None
    return name.lower()


def check_links(path, lines: list[str], rep, index: dict[str, set[str]]) -> None:
    """Rules 6 and 7: every [[link]] and ![[embed]] must find its note and heading.

    Links in code fences and inline code are skipped; links in callouts count.
    An empty target ([[#heading]]) points to this note. A heading part that
    starts with ^ is a block reference: only the note is checked.
    """
    lines = clean_lines(lines)
    mask = fence_mask(lines)
    own_headings = _heading_set(lines)
    for n, line in enumerate(lines, 1):
        if mask[n - 1]:
            continue
        for match in WIKILINK_RE.finditer(_hide_code(line)):
            link = match.group(2).split("|", 1)[0].rstrip("\\")
            target, _, heading = link.partition("#")
            target = target.strip()
            heading = heading.strip()
            if target:
                key = _note_key(target)
                if key is None:
                    continue
                if key not in index:
                    rep.fail(path, n, f"{match.group()}: no such note '{target}'")
                    continue
                headings = index[key]
            elif heading:
                headings = own_headings
            else:
                continue
            if not heading or heading.startswith("^"):
                continue
            parts = [p for p in heading.split("#") if p.strip()]
            if any(_normalize_heading(p) not in headings for p in parts):
                rep.fail(path, n, f"{match.group()}: no such heading '{heading}'")
