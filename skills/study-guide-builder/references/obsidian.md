# When the target is Obsidian

Rules for a guide that lives in an Obsidian vault and uses the Spaced Repetition plugin for flashcards. Step 0 sets the target. In Obsidian mode, these rules replace the GitHub rules for answer blocks, links, and flashcards. Every other step in `SKILL.md` still applies.

The plugin facts come from release 1.15.4 of `st3v3nmw/obsidian-spaced-repetition`. The link rules come from the Obsidian help page "Internal links".

## Set up the plugin first

The reader installs the plugin and changes three values in its settings. One more value stays at its default. The defaults in the plugin's `src/data/settings.ts` break a study guide.

| Setting | Default | Value for the guide | Reason |
|---|---|---|---|
| Single-line card separator | `::` | `;;` | T-SQL (`SCHEMA::Sales`) and Dataview inline fields (`key:: value`) both use `::`. |
| Single-line reversed separator | `:::` | `;;;` | Same reason. |
| Convert highlights to clozes | on | off | Every `==highlight==` becomes a card. |
| Convert folders to decks | off | off (keep) | Folder mode turns every vault folder into a deck. |

Keep highlight clozes off while `;;` is the separator. The plugin's cloze syntax also uses `;;` as a hint marker (`src/data/settings.ts:110`). A cloze line can then turn into a one-line card.

The separators are a setting of this skill too. The defaults are `;;` and `;;;`. If the vault uses other separators, write the cards with those and give them to the checker (see "Run the checker"). The multi-line separators stay at the plugin defaults, `?` and `??`.

Keep the flashcard tag `#flashcards`. Give each note that holds cards the nested tag `flashcards/<guide>` in its frontmatter. The nested tag makes a subdeck for the guide. The plugin reads cards only from tagged notes, so no other vault note is affected.

```yaml
---
tags:
  - dp700
  - study
  - flashcards/dp700
---
```

Keep the guide's tags apart from the vault's stack tags. If the vault lists them in `wiki_stack` in `_meta/config.md`, use none of them. So a DP-700 guide gets no `fabric` or `airflow` tag. The vault skill searches the `tags:` lines of every note for capture and hub work, and a stack tag pulls study notes into that work.

## The order of a note

1. Frontmatter with the tags.
2. The `# Title`.
3. The optional "Do this" callout and checklist.
4. The Step 4 template: why this exists, `## Glossary`, the §sections with their quick checks.
5. `## Teach it back`, then `## What's next`.
6. The card sections, last.

## Fold the answer, not the question

```markdown
> **Quick check:** Which item sends one stream to several destinations?
> A. Eventhouse
> B. Eventstream
> C. Lakehouse
> D. Notebook

> [!question]- Answer
> **Answer: B**
> The eventstream routes events in flight. An eventhouse stores them for queries.
```

The question stays visible. Only the answer folds.

Put a blank line between the question block and the answer callout. Without it, Obsidian merges them into one blockquote and the answer shows.

Write the answer in a folded callout. The `-` after the type folds it: `[!question]-`. A `+` or no sign leaves the callout open, and the checker fails it.

For a multiple-choice question, the first line of the answer is `**Answer: X**`, then the reasoning. Never put an `**Answer: X**` line outside a callout.

One question per callout. Never nest a `[!question]` callout inside another callout. The question must be visible above the answer callout, and a nested callout has no visible block of its own above it.

Never use `<details>` in Obsidian mode. Obsidian does not render Markdown inside raw `<details>` HTML, and a blank line ends the HTML block.

**The answer region.** The checker treats three kinds of callout as an answer region:

- a `[!question]` callout,
- a callout whose own body holds `**Answer:` (lines of a nested callout do not count),
- a callout whose title starts with Answer or Solution.

Every answer region must fold (`-`) and must have a body.

**The visible question.** The checker reads the visible block directly above each `[!question]` callout. The block is a quoted paragraph, a code block, or both. The check passes in two cases. The block holds a `**Quick check:**` or `**Question N:**` label. Or its last line is an option line (`A.` to `D.`). A code-completion question and a multi-line scenario pass, because the label sits at the top of the same block:

~~~markdown
> **Quick check:** Complete the query so it returns ten rows.
> ```kql
> Events
> | ____ 10
> ```

> [!question]- Answer
> `take`. The full query is `Events | take 10`.
~~~

**Mock-exam questions** use the same shape with a `> **Question N:**` label. End each answer with a wikilink to the note that teaches it.

```markdown
> **Question 7:** Which item routes events in flight?
> A. Eventhouse
> B. Eventstream
> C. Lakehouse
> D. Notebook

> [!question]- Answer
> **Answer: B**
> The eventstream routes events. See [[dp700-10-eventstream#§1 Route events in flight]].
```

## Code drills

~~~markdown
> [!example]- Code drill (KQL)
> Complete the query so it counts events per device in Washington.
> ```kql
> Events
> | where State == "WA"
> | summarize count() by ____
> ```
> > [!example]- Solution
> > ```kql
> > Events
> > | where State == "WA"
> > | summarize count() by DeviceId
> > ```
~~~

Put the blanked code in the visible part of the drill. Put the solution in a nested callout with the title `Solution`. A title that starts with Solution makes the callout an answer region, so it must fold.

Fold the drill callout too: `[!example]-`.

The plugin reads code inside callouts. It skips only fences that start at column 0 (`parser.ts:190`). So code in a callout follows the same card rules as prose:

- Write `==` with a space on both sides (`x == 1`). Without the spaces, `x=="a" and y=="b"` reads as a highlight, and a highlight can become a card.
- Keep `;;` and `;;;` out of the code. If the code needs them, put it in a column-0 fence outside the callout.
- Never let a code line be only `?` or `??`.

## Links

Link to another note with a wikilink: `[[dp700-10-eventstream]]`. Link to a heading with `[[note#heading]]`. Link to a heading in the same note with `[[#heading]]`. Show other text with an alias: `[[dp700-99-revision|the revision note]]`.

Every link and every embed (`![[...]]`) must find its note in the guide folder. Every heading part must be a heading in that note. The checker ignores case in note names and headings, and extra spaces in headings. It skips links to URLs, embeds of attachments such as `![[diagram.png]]`, and links in code. For a `#^` block reference, it checks the note only.

Seven characters can break a link (Obsidian help, "Internal links"): `#`, `|`, `^`, `:`, `%%`, `[[`, `]]`. Keep them out of every heading that a link points to. A card heading must never contain one, because the revision note embeds it.

## Flashcards

Card syntax, with the default separators (plugin docs, `docs/docs/en/flashcards/q-and-a-cards.md`, release 1.15.4):

| Card | Syntax |
|---|---|
| One-line | `question;;answer` |
| One-line, reversed | `question;;;answer` |
| Multi-line | question lines, a line that is only `?`, answer lines, then a blank line |
| Multi-line, reversed | the same, with `??` instead of `?` |

A multi-line card:

```markdown
Which item routes one stream
to several destinations in flight?
?
Eventstream
```

Write cards only in card sections (next part). Outside a card section, the plugin reads a separator, a `==highlight==`, or a line that is only `?` or `??` as a card. This also holds inside callout code blocks.

Outside card sections, a separator is safe only in inline code, as in `question;;answer` in this sentence, or in a column-0 fence.

On a card line, never put the separator in inline code before the real separator. The plugin tests only the first separator on a line for inline code. Its `hasInlineMarker` finds that first one with `indexOf` (`parser.ts:62-72`). If that first separator sits in inline code, the plugin does not read the line as a card. The checker fails such a line.

Keep the separators out of the lines of a multi-line card. The plugin reads a line with a separator as a one-line card and drops the multi-line card (`parser.ts:148-157`). The checker fails such a line.

The plugin saves the review history in an SR comment on the line after each card, for example `<!--SR:!2024-08-16,51,230-->` (plugin docs, `data-storage.md`). Each triple holds the due date, the interval, and the ease.

## The card section

```markdown
## Eventstream (card)

| Field | |
|---|---|
| What it is | Routes events in flight |
| Use it when | One stream needs several destinations |
| Not when | You must query the history → use an eventhouse instead |
| Key facts | No code is necessary |
| Docs | Learn page · search words: "eventstream overview" |

Route events to several destinations in flight;;Eventstream
```

Give each component one card section. The heading is `## <Component> (card)`: the name, one space, then `(card)`. The section runs to the next heading of the same or a higher level.

The table comes first, with five fields in this order: What it is, Use it when, Not when, Key facts, Docs. Key facts holds 2 to 4 facts that change a decision. The example shows one, to stay short. Docs names the exact page and the search words that find it.

The exam triggers go under the table, one per line, in card syntax: a scenario phrase, the separator, the answer. Add a concept card only where a trigger line cannot carry the idea.

Never put a separator in a table row. The plugin reads such a row as one card, with the pipes in the question and the answer. The same goes for a heading line and for code that does not start at column 0 (quoted or indented) in the section.

In a card section, every line is a trigger line, except table rows, blank lines, headings, code, and SR comments. Every trigger line must be a card. Put any other text above the card heading.

Trigger lines stay visible. They are the one exception to the collapse rule. The card is the revision layer that the reader reads, and the plugin's review deck hides the answer during practice. This last point comes from the DP-700 study-guide design (anti-goal 2), not from the plugin docs.

Cards come last in the note, after `## Teach it back` and `## What's next`. A heading embed runs to the next heading. So a card at the end of the note embeds without extra text.

A revision note embeds every card, in topic order:

```markdown
![[dp700-10-eventstream#Eventstream (card)]]

![[dp700-10-eventstream#Eventhouse (card)]]
```

## The "Do this" callout and the checklist

```markdown
> [!todo] Do this
> Watch: <video title and link>. Lab: <lab title and link>. Try: <one task in the trial workspace>.
> Video gaps: <where the video differs from the current outline, or "none found">.

- [ ] Video watched
- [ ] Lab done
- [ ] Quick checks answered
- [ ] Teach-back passed
```

Both are optional. Put them at the top of the note, under the title.

The callout names the video, the lab, and one task to try. Note, video, and lab then form one study unit.

The Video gaps line names each place where the video differs from the current outline. If you found none, write "none found". Where they differ, teach the outline, not the video.

The checklist uses plain task lines (`- [ ]`). The Tasks plugin and a Dataview table in the start note can then show the open items of each note.

The "Do this" callout stays open. It holds no answer, so it needs no fold.

## Refresh an Obsidian guide

Refresh mode in `SKILL.md` works on an Obsidian guide, with these rules on top. For cards, they replace the Step 7 rule that derived aids regenerate: edit card lines and SR comments in place. Other derived aids still regenerate.

1. If the guide's reference note holds an outline ID map, map the IDs again against the current outline. Do this before any other change. The IDs come from the order of the outline bullets, so a new or removed bullet shifts them.
2. Never delete or move an SR comment. It holds the reader's review history.
3. For an unchanged card, leave the SR comment as it is.
4. For a card whose answer changes, edit every triple in its SR comment. Keep the ease (the third value). Set the interval (the second value) to 1. Set the due date to the refresh date. A reversed card has two triples, so change both.

A refresh on 2026-11-09 changes the answer of a card. Its SR comment goes from `<!--SR:!2026-08-16,51,230-->` to `<!--SR:!2026-11-09,1,230-->`.

The reset makes the reader relearn the changed fact and see it again within days. Without it, the next good review grows from the old interval, and a corrected fact can stay away for months. The ease stays, so the review history survives the refresh.

## No other HTML comments

Write no HTML comment except the SR comments that the plugin writes. The plugin parser skips the line after a one-line comment, and the rest of the file after an unclosed `<!--` (`parser.ts:107-112`). A comment in a column-0 code fence or in inline code is safe.

## Run the checker

Run it from the folder next to `SKILL.md`, on the whole guide folder. Links resolve only against the notes checked in the same run.

```bash
python3 scripts/check.py --target obsidian <guide folder>
```

The full form is `python3 scripts/check.py --target obsidian [--card-separator TEXT] [--reversed-separator TEXT] <guide folder>`. The separator defaults are `;;` and `;;;`. If the vault uses other separators, give them with these two options.

It fails on:

| Check | Why |
|---|---|
| A merge-conflict marker | A merge left the note broken. |
| An odd number of code fences, also inside callouts | A block never closes, and the rest of the note becomes code. |
| A glossary term that never appears in the body | Every glossary entry must earn its place (Step 4). |
| An answer skew: one letter is more than 50% of 8 or more answers in a note, answers in callouts included | The reader can guess the letter without the knowledge. |
| A `<details>` tag | Obsidian does not render Markdown inside it. |
| An answer region that does not fold (`+` or no sign) | The eye reaches the answer before the guess. |
| An empty answer region | The reader gets no answer to check. |
| An `**Answer: X**` line outside a callout | The answer is visible. |
| A `[!question]` callout without a visible question above it | The question folds with the answer, or it is missing. |
| A `[!type]` line directly under a quoted line of the same or a deeper level, with no blank line between them | Obsidian shows the line as text, not as a callout. The answer or the solution shows. |
| A trigger line in a card section that is not a card, or a multi-line card without question lines or answer lines | The plugin does not read the line as the card you meant. |
| A card line whose first separator sits in inline code | The plugin skips the line. |
| A separator in a line of a multi-line card | The plugin reads that line as a one-line card and drops the multi-line card. |
| A separator in a table row, a heading, or code that does not start at column 0 (quoted or indented) in a card section | The plugin reads the line as a card. |
| A card heading with one of the seven link-breaking characters | The embed link to the card breaks. |
| Outside card sections: a separator outside inline code and column-0 fences, a line that is only `?` or `??`, or a `==highlight==` | The plugin reads these as cards, also in callout code. |
| An HTML comment that is not an SR comment | The plugin can skip the next line, or the rest of the file. |
| A wikilink or embed to a note that is not in the guide folder | The link is dead. |
| A `[[note#heading]]` link or embed whose heading does not exist | The link opens the wrong place, or the embed is empty. |

It warns on:

| Check | Why |
|---|---|
| An answer lean: one letter is more than 40% of 8 or more answers in a note | The distribution starts to skew. |
| A bare "Section N" reference | Name the note, or use `§N` for the current note. |

Fix every FAIL. Read every WARN. To fix a skew, shuffle the options as Step 8 describes. In Obsidian mode, the answer letters sit in the answer callouts.

The GitHub-only checks do not run in Obsidian mode: `<details>` balance, blank lines around `<summary>`, stacked lines, and option lines without an answer line. Obsidian does not merge stacked lines while `strictLineBreaks` is off in `.obsidian/app.json`.
