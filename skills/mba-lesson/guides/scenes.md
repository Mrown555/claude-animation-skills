# Lesson spec and scene catalogue

A lesson spec is `specs/Lnn.json`. A working example of every scene type is in `tests/example_project/specs/` (EOQ, reorder point, ABC).

```json
{
 "id": "L01", "title": "Inventory costs and the EOQ model", "topics": ["T1", "T2"],
 "vars":   {"D": {"value": 12000, "page": 5, "unit": "units per year"}, "EOQ": {"expr": "sqrt(2*D*S/H)"}},
 "checks": [{"expr": "abs(EOQ - 632.46) < 0.005", "note": "matches page 5"}],
 "scenes": [ { "id": "...", "type": "...", "source": {"pages": [4]}, "narration": ["...", "..."], ...type fields } ]
}
```

## Common scene fields
- `narration`: list of sentences, each spoken on its own; a sentence takes 3 to 12 s. A sentence may be `{"text": "...", "say": "how to pronounce it", "pause": 0.8, "voice": "af_heart"}`.
- `narration_hi`: optional Hinglish list, the same length (only for `--lang hinglish`).
- `source: {"pages": [..]}` **or** `"supplementary": true`. Shown on screen as "Notes · p. 4" or "Beyond the notes".
- **Cues.** Any item with `"at": n` appears when sentence `n` (0-based) starts, plus `delay` seconds (default 0.1, or 0.6 for sentence 0). Give every item an explicit `at`; sound effects follow these cues.
- `hold`: extra seconds at the end of the scene.
- **Text.** `**bold**` becomes accent colour, and `$...$` is inline maths (KaTeX). `{{var}}`, `{{var|2}}` (decimals), `{{var|0}}`, `{{var|in}}` (Indian grouping) or `{{var|%}}` insert computed values. Never type a computed number by hand.
- **Narration** is plain spoken English: no TeX. Write "E O Q" for letters that should be spelled out (acronyms in capitals are spelled automatically), and "₹500" is read as "500 rupees".

## Scene types
| type | use for | fields (limits) |
|---|---|---|
| `title` | lesson opener | `kicker`, `title`, `subtitle` |
| `concept` | a definition | `term`, `definition`, `gloss` (plain words), `points[]` ≤4 `{text, at}`, `definitionAt`, `glossAt` |
| `bullets` | key points, stories, `variant: "recap"` | `heading`, `items[]` ≤6 `{text, sub, at}`, `numbered`, `callout {title, text, at, supplementary}` |
| `table` | comparisons, classifications | `heading`, `columns[]`, `widths[]` (css fr), `rows[]` ≤7 `{cells[], at, highlight}` |
| `formula` | a formula, term by term | `heading`, `latex` with `\htmlClass{t1}{D}` around term 1, `t2` around term 2 and so on, `terms[] {sym, label, at}`, `formulaAt`, `finalAt`, `size` |
| `calc` | a numerical example | `heading`, `given[] {sym, label, value, at}`, `steps[]` ≤6 `{note, tex, at}`, `result {tex, text, at}`. With no `given` and 4 or more steps, the layout is two columns. |
| `chart` | curves, trends, cost trade-offs, inventory over time | `heading`, `x {label,min,max,ticks}`, `y {...}`, `series[] {name, fn: "D/x*S" or gen: {Q,T,cycles,base} or points, from, to, color, dash, at, drawTime}`, `marks[] {x, y, label, at}`, `notes[]` ≤3 `{text, at, color}`. Numbers may be var names or expressions. |
| `process` | flows, sequences, cycles | `heading`, `steps[]` ≤5 `{label, title, text, at}`, `loop` (true or a label) |
| `matrix` | 2x2 frameworks (BCG, SWOT, Ansoff) | `heading`, `xlabel`, `ylabel`, `cells[4] {title, text, at, color}` (top-left, top-right, bottom-left, bottom-right) |
| `roleplay` | HR, sales, negotiation, customer scenes | `characters[2] {name, color: blue/red/green/yellow/navy/purple}`, `setting: office/store/plain`, `lines[] {who: 0/1, text, at}`. Narrate the lines themselves and give the second character another voice (`"voice": "af_heart"`). |

Colours: `var(--accent)` teal, `var(--accent2)` orange, `var(--accent3)` indigo, `var(--good)`, `var(--bad)`, `var(--ink)`. Set `"theme": {"accent": "#..."}` in `project.json` for a subject colour.

## Choosing scenes by subject
- **Operations / supply chain:** `process` flows, `chart` for trade-offs and stock over time, `formula` + `calc`, `table`.
- **Finance / accounting:** `formula` + `calc` for every ratio, `chart` for cash flows and NPV curves, `table` for statements.
- **Statistics / economics:** `chart` (distributions via `fn`, supply and demand), `formula`, `calc`.
- **Marketing:** `roleplay` with customers, `process` for the customer journey or funnel, `matrix` for STP, BCG or Ansoff.
- **HR / OB:** `roleplay` (interviews, appraisals, conflicts), `process` (recruitment), `table` (theories compared).

Keep one idea per scene (30 to 70 s). Mix types: never more than two text-only scenes in a row.

## Visual styles
`project.json` → `"style": "clean"` (default, light) or `"style": "kurzgesagt"` (flat-vector space look: navy-purple sky, stars, a glowing planet, bright accents; inspired by the style, not affiliated). The style only changes colours, fonts and the background; every scene type works in both. Scene colours should use the theme variables (`var(--accent)`, `var(--paper)`, ...), never hard-coded hex values, so new styles can be added in `theme.css` with one `:root[data-style="..."]` block.
