---
name: study-guide-builder
description: Build grounded, easy-to-understand study material (a study repo, a learning guide, a tutorial, explainer notes) for someone learning a technical topic for the first time. Grounds facts via Exa and Context7, writes in plain short sentences, and applies density/clarity fixes learned on real study-repo builds. Use when asked to create a study guide, learning material, a tutorial, prep notes for an interview/exam, to "teach me" / "explain X so I actually understand it" for a technical topic, or to refresh or grade an existing study guide.
---

Build study material that a first-time learner can read in one pass, not a reference dump. Every rule below came from a corrective round on a real build. The stories behind the rules are in `references/lessons.md` — read it when a rule seems optional. If the material pairs with a slide deck, also read `references/slide-decks.md`. If the target is Obsidian, also read `references/obsidian.md`.

Three modes. **Build** runs Steps 0 to 8 in order. **Refresh** updates an existing guide (see the end of this file). **Teach-back** grades a reader's own explanation (Step 4).

Terminology: a **file** is one markdown file in the study repo. A **§section** is a numbered heading inside one file. Never write a bare "Section 3" in the material — name the target file, or use `§3` for the current file.

## Step 0 — Grill before you build

A request to "build a study guide for X" is never fully specified. Run an intake in rounds of clickable questions (the AskUserQuestion tool). Give every question a recommended option, marked "(Recommended)" and listed first. After each round, ask whatever the answers unblocked. Stop when nothing that shapes the guide is unsettled.

**Round 1 — scope.** One round, six questions. One call takes at most four questions, so ask them in two calls:

- **Where it lives and how big.** One file, or a multi-file repo? Which folder or repo name? For a repo, settle GitHub and visibility now (Step 7).
- **Depth, self-reported.** First-time learner, or a denser refresher? This is a claim — round 2 tests it.
- **Adjacent domain.** What does the reader already know? This unlocks the bridge file (Step 3).
- **Goal.** Interview, exam, project, or general learning? With no goal, skip the goal callouts in Step 4 and round 3.
- **Time budget.** Three days and three weeks produce different guides. Scope file count and depth to the answer.
- **Output target.** GitHub (Recommended) or Obsidian. The Obsidian target folds answers in callouts, links notes with wikilinks, and writes flashcards for the Spaced Repetition plugin. For Obsidian, read `references/obsidian.md` before you write.

**Round 2 — calibration quiz.** Ask 3 to 5 multiple-choice questions on the topic, pitched at the claimed depth. Ground the quiz facts first (Step 1) — a wrong answer key miscalibrates everything after it. The answers, not the self-report, set the starting level: a wrong answer marks something to teach from scratch; a confident right answer marks something to compress or skip.

This round is the exception to the "(Recommended)" rule. A calibration question has no recommended option, because the mark gives the answer away. Spread the correct answers over the option positions.

**Round 3 — goal interrogation** (only with a named goal). Work backwards from the event: What will you be asked? What must you be able to do on day one? What does failure look like? The answers become the targets for the "Worth asking" callouts and the self-tests.

**Feedback scope.** Mid-build feedback on one example ("this passage is too dense") usually means "fix this pattern everywhere." Ask, or state your scope assumption, then say explicitly whether you fixed the pattern everywhere. When the reader reveals their real background late, patch what is already written, not only future files.

## Step 1 — Ground every fact

Never write a checkable fact from memory. This holds hardest for product names, API shapes, SDK versions, pricing, and model names.

- **Exa** is the preferred search tool. Check for a key before you conclude that it is absent: the `EXA_API_KEY` environment variable, a project `.env` file, then macOS Keychain:
  ```bash
  export EXA_API_KEY="$(security find-generic-password -s EXA_API_KEY -w)"
  curl -s -X POST 'https://api.exa.ai/search' -H "x-api-key: $EXA_API_KEY" -H 'Content-Type: application/json' \
    -d '{"query":"...","numResults":3,"type":"auto"}'
  ```
  `/contents` with a `urls` array fetches full page text. If no key exists anywhere, tell the user and ask before you substitute WebSearch.
- **Context7** (`resolve-library-id`, then `query-docs`) covers library-specific facts: call shapes, config fields, import paths. Prefer it over web search for those.
- Live-check any company or product that renames itself often, even when you feel confident.
- **Cite load-bearing facts, but not in the reading path.** A version, price, product name, or date gets a markdown link to its source. Put the link in the guide's `reference_*.md` file (Step 4), or in a short "Sources" list at the end of the file. A sentence in a teaching section carries no link. Refresh mode greps the whole guide folder, so the links still work.

## Step 2 — Plain, short sentences

If the `simple-english` skill is installed, load it and apply pragmatic mode throughout. If not, apply its core rules directly: ~25-word sentence limit, active voice, no semicolons, no `should`/`would`/`could`/`might`, conditions before commands, no contractions. Domain vocabulary stays — this is about sentence load, not dumbing down.

## Step 3 — Bridge file (file `00`)

If the topic is new but the reader knows an adjacent domain, write a bridge file first, numbered `00`. Do not teach a domain from first principles when the reader owns the same machine under different names.

Four parts, in this order:

1. **The claim, stated plainly.** "These are the same mechanism." Then one worked example told twice — once in the familiar domain, once in the new one, same shape and numbers.
2. **The translation table.** Familiar term, new term, and a third column that names the shared idea.
3. **Where the analogy breaks.** Non-negotiable, and usually the most valuable part. Name the differences, and say which one causes the real difficulty.
4. **The short retention list.** About nine terms, not forty. Name the three that carry most of the conversation.

Ground the familiar side too.

## Step 4 — One template for every file

1. **A short "why this exists" framing** — what problem the file solves, tied to the reader's goal when there is one.
2. **A `## Glossary`** before the main content: every jargon term used in the file, one plain line each. Define once, then use. Never invent an entry to fill space — every term must appear in the body (checked in Step 8).
   A glossary row is not an explanation. Explain each term in the body where it first matters: the definition, the thing it replaces, and the consequence for this project. A file that states conclusions without laying that ground reads as ammunition, not learning material.
3. **The main content**, written to the Step 5 cut rule. Lead each §section with a concrete example, then the general rule. For a framework or library, show the plain-language or plain-Python version of the idea first, then the framework's version, and match them line by line. Explain a syntax the reader has not met (`Enum`, `list[X]`, `yield`, `async`) in one or two lines with an everyday picture, then move on. For any multi-step process, show a worked trace with the output of every step — the actual input, what each step produces, what comes back. A list of step names teaches nothing.
4. **A "Quick check" at the end of each major §section** — one question that applies the concept to a new scenario, never "summarize this".
5. **A "Teach it back" prompt at the end of the file** — one line: `> **Teach it back:** Explain <the file's core idea> in two or three sentences, in your own words, to Claude.` One per file, on the idea the file exists to teach.
6. **A "what's next" pointer**, if the file is part of a series.

**Reference material leaves the reading path.** Version numbers, region lists, CLI flags, import paths, metric names, prices, legal article numbers, and comparison tables of tools belong in a `reference_<topic>.md` file, not in the numbered files. The numbered file names the fact in one clause and points to the reference file. Test each table in a numbered file: does a first-time reader need every row to follow the section? If not, move it. A reference file has no glossary, no quick checks, and no teach-back. It is lookup, and it carries the source links.

With a named goal, add sparse callouts: `> **Worth asking:** ...` — a real, answerable question grounded only in established facts. Add one only where a concept genuinely connects to the goal.

**Every Q&A aid hides its answer in a collapsed block** — quick checks, flashcards, practice questions, multiple-choice tests. No visible answer-key tables anywhere: an answer the eye can reach before the guess defeats retrieval.

**The `<details>` block (GitHub target).** For the Obsidian target, use the folded callout in `references/obsidian.md`.

```
> **Quick check:** <question>

<details>
<summary>Answer</summary>

<the answer, then the reasoning — 1 to 4 sentences, tied only to content already in this file>

</details>
```

For a multiple-choice question, the first line inside the block is `**Answer: <letter>**`, then the reasoning. Keep a blank line after `<summary>` and before `</details>`, or GitHub renders literal HTML. Never ship `<details open>`. One question per block.

**Grading a teach-back.** When the reader sends their explanation, grade it against the file's glossary and its main claims, not against a keyword list. Reply in three parts, short: what they got right, what is missing or wrong (with the fix in one sentence each), and one follow-up question that probes the weakest part. If the explanation is right, say so plainly and ask nothing more. If the same gap appears in two teach-backs, the file is at fault — offer to rewrite that §section.

## Step 5 — Cut what changes no decision

The test: can the reader use the concept correctly without this fact? Would knowing it change what they build, ask, or decide? If no to both, cut it or compress it to one clause.

This mainly hits mechanism trivia: file-format internals, obscure parameters, statistical derivations, version history, byte-level detail. Keep failure modes, tradeoffs, worked numeric examples, code the reader will write, and the reasoning behind design choices.

Do not re-derive reasoning in summaries. A closing section states each conclusion in one clause.

Where a concept maps to a real tool, name it: not "a layout-aware parsing tool exists" but "a tool like **Docling** handles this." A named tool is the difference between a concept and something actionable.

## Step 6 — Real diagrams and tables

- Branching or decision logic becomes a Mermaid flowchart — never ASCII arrows, never a numbered list of bolded questions. If you are numbering questions, it is probably a flowchart.
- A comparison, failure-mode list, or fact-and-mitigation pairing becomes a markdown table.
- Sequential reasoning stays prose. A flowchart with one path per node is a list with extra syntax.
- Keep every Mermaid node label to a handful of words. Long labels clip in real renderers.
- A block of label-and-value facts is a two-column table, never stacked `**Label:** value` lines — markdown merges them into one paragraph. A bold label above a list or table needs a blank line under it.

## Step 7 — Multi-file repos

- Study material often names real people and the reader's weaknesses: fine in a private repo, not in a public one. Check `gh repo list` for the user's usual pattern. Ask before you push.
- Number files by learning order. Cross-file references name the topic ("the Pydantic file"), never a bare number. `§N` refers only to the current file's own sections.
- Build a master glossary grouped by topic, not 1:1 by file — merge files that are one continuous concern.
- Derived aids (cheat sheet, flashcards, practice questions) regenerate together with the source content, every pass. They drift silently otherwise.
- Obsidian target exception: edit card lines and their SR comments in place, never regenerate them. The SR comment under each card holds the reader's review history. Follow the refresh rules in `references/obsidian.md`.

## Step 8 — Verify, do not just report done

Run the checker from the folder next to this file, on the guide's folder:

```bash
python3 scripts/check.py <guide folder>
```

It fails on: merge-conflict markers, an odd number of code fences, unbalanced or pre-opened `<details>` blocks, a missing blank line around `<summary>` and `</details>`, glossary terms that never appear in the body, and a skewed multiple-choice answer distribution. It warns on stacked lines that merge into one paragraph, bare "Section N" references, and multiple-choice options with no `**Answer: X**` line. Fix every FAIL. Read every WARN — list items and soft-wrapped prose are false positives, stacked facts are not. The Obsidian target has its own list of checks in `references/obsidian.md`. To run it, add `--target obsidian`:

```bash
python3 scripts/check.py --target obsidian <guide folder>
```

Then, by hand:

- Re-read the whole document once for sentence load: over-limit sentences, contractions, `has been`, long compound sentences that felt short.
- After inserting a new section (a primer, a bridge) ahead of existing content, re-check reading order: the new section must not reference an example that only appears later.
- If parallel agents did the work, read a sample of the output yourself. Self-reports describe intent, not results.
- If the answer distribution skews, fix it with a script that shuffles each question's options and rewrites the answer lines. Then verify: the set of option texts per question is unchanged, and every answer letter still points at the originally correct option. Rerun the checker.

## Refresh mode

Use it when asked to refresh, update, or recheck an existing guide, or via `/study-guide refresh <path>`.

1. **Collect the claims.** Grep the guide for inline source links (Step 1) and for facts that age: version numbers, prices, model names, product names, dates, "latest", "currently". List each with its file and line.
2. **Recheck each claim** with Exa or Context7. Fetch the linked source first. If the link is dead or the page changed, search for the current fact.
3. **Report before you edit.** One table: claim, what the guide says, what is true now, source. Mark each row unchanged, changed, or unverifiable. Stop and show the table.
4. **Apply approved changes only.** Update the text and the link. If a changed fact invalidates a worked example or a quiz answer, fix those in the same pass.
5. **Regenerate derived aids** (Step 7) and run the checker (Step 8). In Obsidian mode, follow the refresh rules in `references/obsidian.md`.

Do not rewrite prose that is still true. A refresh changes facts, not style.
