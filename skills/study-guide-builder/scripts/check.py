#!/usr/bin/env python3
"""Check a study guide for the mechanical faults listed in SKILL.md, Step 8.

Usage:
    python3 check.py [PATH ...]
    python3 check.py --target obsidian [--card-separator TEXT] [--reversed-separator TEXT] [PATH ...]

PATH is a markdown file or a folder. Folders are searched recursively.
With no PATH, the current folder is checked.

--target github (the default) checks a guide written for GitHub.
--target obsidian checks notes written for Obsidian and the Spaced Repetition
plugin: callouts, card sections, and links between the notes checked together.
--card-separator and --reversed-separator give the plugin's one-line card
separators (defaults ';;' and ';;;').

Prints one line per finding, FAIL or WARN, then a summary.
Exit code is 1 when there is at least one FAIL. WARN lines do not change it.
"""
import argparse
import pathlib
import re
import sys
from collections import Counter

_HERE = str(pathlib.Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)  # find obsidian_checks next to this file, from any working folder

import obsidian_checks  # noqa: E402

SKIP_DIRS = {".git", "node_modules", ".venv", "venv"}
ANSWER_RE = re.compile(r"\*\*Answer: ([A-D])\*\*")
OPTION_RE = re.compile(r"^\s*(?:[-*]\s+)?\(?[A-D][.)]\s+\S")
BARE_SECTION_RE = re.compile(r"\bSection \d+\b")
GLOSSARY_HEADING_RE = re.compile(r"^(#{1,6})\s+glossary\b", re.IGNORECASE)
CONFLICT_RE = re.compile(r"^(<<<<<<< |=======$|>>>>>>> )")


class Report:
    def __init__(self):
        self.fails = 0
        self.warns = 0

    def fail(self, path, line, msg):
        self.fails += 1
        print(f"FAIL {path}:{line}: {msg}")

    def warn(self, path, line, msg):
        self.warns += 1
        print(f"WARN {path}:{line}: {msg}")


def markdown_files(paths):
    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*.md")):
                if not SKIP_DIRS.intersection(f.parts):
                    yield f
        elif p.suffix.lower() == ".md" and p.exists():
            yield p
        else:
            print(f"WARN {p}: not a markdown file or folder, skipped")


def is_fence(line):
    return line.strip().startswith("```")


def fence_mask(lines):
    """True for lines inside a code fence, including the fence lines."""
    mask = []
    inside = False
    for line in lines:
        if is_fence(line):
            inside = not inside
            mask.append(True)
            continue
        mask.append(inside)
    return mask


def check_conflicts(path, lines, rep):
    for i, line in enumerate(lines, 1):
        if CONFLICT_RE.match(line):
            rep.fail(path, i, "merge-conflict marker")


def check_fences(path, lines, rep):
    count = sum(1 for l in lines if is_fence(l))
    if count % 2:
        rep.fail(path, 0, f"odd number of code fences ({count}); a block never closes")


def strip_quote(line):
    """Remove a leading blockquote marker and inline code spans, so '> <summary>' is seen as '<summary>'."""
    line = re.sub(r"`[^`]*`", "", line)
    return re.sub(r"^(\s*>\s?)+", "", line).strip()


def check_details(path, lines, mask, rep):
    opens = closes = 0
    for i, line in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        s = strip_quote(line)
        if "<details open" in s:
            rep.fail(path, i, "<details open>: answer is visible before the guess")
        opens += s.count("<details")
        closes += s.count("</details>")
        one_liner = "<details" in s and "</details>" in s
        if one_liner:
            continue
        if s == "</details>":
            prev = strip_quote(lines[i - 2]) if i >= 2 else ""
            if prev:
                rep.fail(path, i, "no blank line before </details>; GitHub renders literal HTML")
        if s.startswith("<summary>") and s.endswith("</summary>"):
            nxt = strip_quote(lines[i]) if i < len(lines) else ""
            if nxt:
                rep.fail(path, i, "no blank line after <summary>; GitHub renders literal HTML")
    if opens != closes:
        rep.fail(path, 0, f"<details> opened {opens} times, closed {closes} times")


def glossary_terms(lines, mask):
    """Return (terms, glossary_line_indexes). Terms come from a '## Glossary' section."""
    terms = []
    section = set()
    level = None
    for idx, line in enumerate(lines):
        if mask[idx]:
            continue
        head = re.match(r"^(#{1,6})\s+\S", line)
        if head:
            if level is not None and len(head.group(1)) <= level:
                level = None
            g = GLOSSARY_HEADING_RE.match(line)
            if g:
                level = len(g.group(1))
                section.add(idx)
                continue
        if level is None:
            continue
        section.add(idx)
        s = line.strip()
        if not s:
            continue
        term = None
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or set(cells[0]) <= set("-: "):
                continue
            first = cells[0]
            if first.lower() in {"term", "word", "name", "concept"}:
                continue
            term = first
        elif re.match(r"^([-*]|\d+[.)])\s", s):
            body = re.sub(r"^([-*]|\d+[.)])\s+", "", s)
            bold = re.match(r"\*\*(.+?)\*\*", body)
            if bold:
                term = bold.group(1)
            else:
                term = re.split(r"\s[—–-]\s|:\s", body, 1)[0]
        if term:
            term = term.replace("**", "").replace("`", "").strip().rstrip(":.;,-–— ").strip()
            if term and len(term.split()) <= 8:
                terms.append((idx + 1, term))
    return terms, section


SUFFIXES = ("ization", "isation", "ation", "tion", "ion", "ing", "ies", "es", "ed", "s")


def normalize(text):
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower().replace("-", " ")).strip()


def stem(word):
    for suf in SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


def term_forms(term):
    """Candidate strings that count as a use of the term."""
    t = re.sub(r"^\([a-z0-9]\)\s*", "", term.strip(), flags=re.IGNORECASE)  # "(a) Prompt-only"
    forms = [t]
    forms.append(re.sub(r"\s*\(.*?\)", "", t))          # drop parentheticals
    forms.extend(re.findall(r"\((.*?)\)", t))           # the parenthetical alone: "(TP/FP)"
    for part in re.split(r",\s*(?:also called|or|aka)\s+|,\s*", t):
        forms.append(part)
    expanded = []
    for f in forms:
        expanded.append(f)
        expanded.extend(x for x in re.split(r"\s*/\s*", f) if x)
    out = []
    for f in expanded:
        n = normalize(f)
        if n and n not in out:
            out.append(n)
    return out


def term_used(term, body_norm, body_words):
    for form in term_forms(term):
        if form in body_norm:
            return True
        words = form.split()
        if len(words) == 1 and len(words[0]) >= 5:
            root = stem(words[0])
            if any(w.startswith(root) for w in body_words):
                return True
    return False


def check_glossary(path, lines, mask, rep):
    terms, section = glossary_terms(lines, mask)
    if not terms:
        return
    body_lines = [l for i, l in enumerate(lines) if i not in section and l.strip()]
    if len(body_lines) < 15 or len(section) > 0.7 * len(lines):
        return  # a standalone master glossary; its terms live in other files
    body_norm = normalize("\n".join(body_lines))
    body_words = set(body_norm.split())
    for lineno, term in terms:
        if not term_used(term, body_norm, body_words):
            rep.fail(path, lineno, f"glossary term '{term}' never appears in the body")


def check_stacked_lines(path, lines, mask, rep):
    run = []

    def flush():
        if len(run) > 1:
            rep.warn(path, run[0], f"{len(run)} stacked lines merge into one paragraph on GitHub")
        run.clear()

    for i, line in enumerate(lines, 1):
        if mask[i - 1]:
            flush()
            continue
        s = line.strip()
        starts_block = (
            not s
            or s[0] in "|#>-<["
            or s.startswith("* ")
            or re.match(r"^\d+[.)]\s", s)
            or line.endswith("  ")
        )
        if starts_block:
            flush()
            continue
        run.append(i)
    flush()


def check_multiple_choice(path, lines, mask, rep):
    answers = []
    depth = 0
    for i, line in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        s = line.strip()
        if s.startswith("<details"):
            depth += 1
        m = ANSWER_RE.search(re.sub(r"`[^`]*`", "", line))
        if m:
            answers.append(m.group(1))
            if depth == 0:
                rep.fail(path, i, "**Answer: X** line outside a <details> block")
        if "</details>" in s:
            depth = max(0, depth - 1)
    option_lines = sum(1 for i, l in enumerate(lines) if not mask[i] and OPTION_RE.match(l))
    if option_lines >= 4 and not answers:
        rep.warn(path, 0, f"{option_lines} multiple-choice option lines but no **Answer: X** line; format drifted?")
    if len(answers) >= 8:
        counts = Counter(answers)
        letter, top = counts.most_common(1)[0]
        share = top / len(answers)
        spread = " ".join(f"{k}={counts.get(k, 0)}" for k in "ABCD")
        if share > 0.5:
            rep.fail(path, 0, f"answer skew: {letter} is {share:.0%} of {len(answers)} answers ({spread})")
        elif share > 0.4:
            rep.warn(path, 0, f"answer lean: {letter} is {share:.0%} of {len(answers)} answers ({spread})")


def check_bare_sections(path, lines, mask, rep):
    for i, line in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        if BARE_SECTION_RE.search(line):
            rep.warn(path, i, "bare 'Section N' reference; name the file, or use §N for this file")


def check_file(path, rep, target="github", seps=None, index=None):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    if target == "obsidian":
        check_obsidian_file(path, lines, rep, seps, index)
        return
    mask = fence_mask(lines)
    check_conflicts(path, lines, rep)
    check_fences(path, lines, rep)
    check_details(path, lines, mask, rep)
    check_glossary(path, lines, mask, rep)
    check_stacked_lines(path, lines, mask, rep)
    check_multiple_choice(path, lines, mask, rep)
    check_bare_sections(path, lines, mask, rep)


def check_obsidian_file(path, lines, rep, seps=None, index=None):
    """Obsidian mode. The GitHub-only checks (details, stacked lines, multiple choice) are skipped."""
    lines = obsidian_checks.clean_lines(lines)
    if seps is None:
        seps = obsidian_checks.Separators()
    if index is None:
        index = obsidian_checks.build_index([path])
    mask = obsidian_checks.fence_mask(lines)
    check_conflicts(path, lines, rep)
    obsidian_checks.check_fences(path, lines, rep)
    check_glossary(path, lines, mask, rep)
    check_bare_sections(path, lines, mask, rep)
    obsidian_checks.check_note(path, lines, rep, seps)
    obsidian_checks.check_links(path, lines, rep, index)


def parse_args(argv):
    parser = argparse.ArgumentParser(prog=pathlib.Path(argv[0]).name if argv else "check.py",
                                     description="Check study guides for mechanical faults.")
    parser.add_argument("paths", nargs="*", default=["."], metavar="PATH",
                        help="markdown file or folder (default: the current folder)")
    parser.add_argument("--target", choices=["github", "obsidian"], default="github",
                        help="where the guide is read (default: github)")
    parser.add_argument("--card-separator", default=";;", metavar="TEXT",
                        help="one-line card separator in Obsidian mode (default: ;;)")
    parser.add_argument("--reversed-separator", default=";;;", metavar="TEXT",
                        help="reversed one-line card separator in Obsidian mode (default: ;;;)")
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    seps = obsidian_checks.Separators(single=args.card_separator, reversed=args.reversed_separator)
    rep = Report()
    files = list(markdown_files(args.paths))
    if not files:
        print("No markdown files found.")
        return 1
    index = obsidian_checks.build_index(files) if args.target == "obsidian" else None
    for f in files:
        check_file(f, rep, args.target, seps, index)
    print(f"\n{len(files)} files checked: {rep.fails} FAIL, {rep.warns} WARN")
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
