---
name: nglspn-taxonomy
description: >-
  Project category taxonomy for the Naglasúpan (nglspn) repo. Use when the user
  asks to rethink, review or propose the project categories, says the current
  categories are too broad, at their limits, or a dumping ground, wants
  sub-categories, wants projects re-filed or re-grouped, or asks about improving
  discovery of projects (issue #77). Also use when asked to check or update an
  existing taxonomy report under docs/taxonomy/.
---

# Naglasúpan project taxonomy

You are proposing how the projects on naglasupan.is should be grouped. The
deliverable is a report — `docs/taxonomy/<YYYY-MM-DD>-report.json` — listing
every project with the category it is in today and the category it belongs in.
Your tooling only ever GETs from the public API: nothing on the site changes,
no migrations, no `ProjectCategory` writes. Someone reads the report and
decides, and a separate command applies it — see **Applying a report** below.
Do not run that command yourself.

## Workflow

1. **Export the truth.** From `src/django-backend/`:

   ```bash
   python3 -m scripts.taxonomy export --api-url https://api.naglasupan.is/api \
       --output /tmp/taxonomy-projects.json
   ```

   Reads the public API — no database, no Django, standard library only. Drop
   `--api-url` to hit a local backend at `http://localhost:8000/api`. Roughly
   two requests per project, so give it half a minute.

   The API only serves **approved** projects, which is the right scope: those
   are the ones discovery has to sort. Drafts and pending submissions are
   invisible here and out of scope.

2. **Read every project.** Judge from tagline, description, long description,
   tags and tech stack. Titles are Icelandic product names and tell you almost
   nothing — a project called `smakk.app` could be anything.

3. **Design the taxonomy** by the rules below.

4. **Write the report** to `docs/taxonomy/<YYYY-MM-DD>-report.json`, schema below.

5. **Verify.** From `src/django-backend/`:

   ```bash
   python3 -m scripts.taxonomy check ../../docs/taxonomy/<date>-report.json \
       --api-url https://api.naglasupan.is/api
   ```

   This re-fetches from the API, so it checks the report against the live site
   rather than against your own export. Errors mean the report is wrong about
   the site — a project missing, an invented project, a project filed under a
   category it isn't in, a placement pointing at a category the report never
   defines. Fix and rerun until it passes.

   `--snapshot /tmp/taxonomy-projects.json` checks against the export file
   instead, which is faster while you iterate — but only the re-fetch catches
   the site having moved under you, so finish on a live run.

   Warnings are shape heuristics (undersized, oversized, empty
   categories): either redraw the grouping or answer each one in
   `observations`. Do not report back before the check is green.

6. **Render the diff** and put it in front of the reader:

   ```bash
   python3 -m scripts.taxonomy diff ../../docs/taxonomy/<date>-report.json
   ```

   Markdown on stdout, straight from the report — no API call, so it works
   offline. It says which categories are added, renamed, split, merged, kept
   and retired; where each of today's categories ends up; every project that
   moves; the low-confidence calls; and the unplaced. `--output PATH` writes it
   to a file instead, for pasting into an issue.

   Paste it into the chat rather than writing your own summary from memory —
   the diff is generated from the report, so it can't drift from it. Add a
   sentence or two on top for the calls you are least sure about. The JSON is
   the artefact; the diff is what gets read.

## What makes a better grouping

- **Group by what a visitor came for** — the domain the project serves and who
  it serves. Not the tech stack (that is what tags are for), not maturity, not
  the author, not when it was submitted.
- **The name carries its own weight.** Two or three words of English (the
  existing categories are English even though the products are Icelandic), at
  most one `&`. A visitor should predict the contents without clicking.
  `Other`, `Misc` and `General` are not categories; they are the absence of one.
- **Size discipline.** Five to nine top-level categories. Each holds at least 3
  projects and no more than 30% of the corpus. A category holding half the site
  is not a grouping, it is the site.
- **Sub-categories only where they earn it.** A top-level with 8+ projects and a
  real internal split. Each sub-category holds 2+ projects. One sub-category
  under one parent is just a rename.
- **One home each.** Exactly one primary placement per project. Where a second
  reading is genuinely defensible, record `alternative_category_slug`. If the
  same two categories keep appearing as primary/alternative, the boundary
  between them is wrong — redraw it rather than logging the ambiguity 20 times.
- **Design for the next hundred submissions**, not the current few dozen. Every
  category states in `future_example` the kind of project that would land there
  next. A taxonomy that only describes today's corpus is obsolete on the next
  batch.
- **Churn costs.** A category slug is a URL (`/category/<slug>`) and every link
  to it. Keep what works and mark it `kept`. A `renamed`, `merged` or `split`
  category has to say in its rationale what the old shape got *wrong* — "the
  new one reads better" does not justify breaking links.
- **Say when you don't know.** Descriptions are often thin or empty. Then
  `confidence: "low"` and say in the rationale what you would need. If a project
  is genuinely unplaceable, leave `proposed_category_slug: null` and list it in
  `unplaced` with a reason — the checker allows exactly that, and an honest gap
  tells the reader more than a confident guess.
- **Cite evidence, not vibes.** Each rationale quotes something concrete from
  the export — a phrase from the tagline or description, a tag, the URL. "Feels
  like a dev tool" is not a rationale. You may open `website_url` when the copy
  is too thin to judge; say so in the rationale when you do.

## Report schema

```jsonc
{
  "generated_at": "2026-08-21",              // the date in the filename
  "source": {
    "api_url": "https://api.naglasupan.is/api"  // where you exported from
  },
  "current_categories": [                    // must match the API
    {"slug": "apps-services", "name": "Apps & Services", "project_count": 18}
  ],
  "proposed_taxonomy": [
    {
      "slug": "civic-tech",                  // kebab-case, unique
      "name": "Civic Tech",
      "status": "kept",                      // kept | renamed | merged | split | new
      // Current slugs this is the successor of. The diff reads these: a
      // current category no entry claims is reported as retired, and a project
      // counts as merely following a rename only when one category claims its
      // old slug on its own and that old slug is gone. In a split every
      // project is re-filed, because the old slug dies for all of them.
      "replaces": ["community-public-good"],
      "rationale": "…what the old shape got wrong / why this line is the right one",
      "future_example": "A tool that surfaces municipal planning notices",
      "subcategories": [
        {"slug": "open-data", "name": "Open Data", "rationale": "…"}
      ]
    }
  ],
  "projects": [
    {
      "id": "…uuid from the export…",
      "slug": "smakk-app",
      "title": "smakk.app",                  // must match the API exactly
      "current_category_slug": "apps-services",   // or null
      "proposed_category_slug": "food-drink",     // or null, then list in unplaced
      "proposed_subcategory_slug": null,
      "alternative_category_slug": null,
      "confidence": "high",                  // high | medium | low
      "rationale": "Tagline: 'finndu vínið þitt' — wine discovery for consumers."
    }
  ],
  "unplaced": [
    {"id": "…uuid…", "reason": "Description is empty and the site is offline."}
  ],
  "observations": [
    "Two categories are only distinguishable by audience; consider merging."
  ]
}
```

## Commands

Both run from `src/django-backend/`, both take `--api-url` (default
`http://localhost:8000/api`).

| Command | Does |
|---|---|
| `python3 -m scripts.taxonomy export --output PATH` | Walks the API for every approved project: copy, tags, tech stack, and the category it is in today |
| `python3 -m scripts.taxonomy check PATH` | Fails if the report misses, invents, retitles or mis-files a project, or places one in a category it never defines |
| `python3 -m scripts.taxonomy diff PATH` | Renders the report as a Markdown diff: categories added, renamed, split, merged, kept, retired; where today's categories go; every move. No API call |

Both build the same snapshot from the same endpoints (`scripts/taxonomy/`), so
the export and the check can't disagree about what the site contains. Neither
needs database access or a Django environment — plain `python3` is enough.

## Applying a report

Not your job, but worth knowing what the report becomes. A checked report is
applied by a Django management command, run by a person against a real
database:

```bash
cd src/django-backend
uv run python manage.py apply_taxonomy \
    ../../docs/taxonomy/<date>-report.json --dry-run   # then again without it
```

It reads `proposed_taxonomy` and `projects`, matches projects on `id`, and takes
`display_order` from the order categories appear in `proposed_taxonomy` — so
that order is an editorial decision, not a formatting detail. It is the sequence
of tabs on `/projects` and of rows on the discover page. Put the categories in
the order a visitor should meet them.

Two things it will not do, which shape what a report should say:

- **It ignores `subcategories`.** Nothing in the schema, the API or the UI
  models a second level. Propose them where they are real — they tell the
  reader where the next split goes — but a report whose top level only works
  once the subcategories exist is a report that cannot be applied.
- **It never deletes a category.** A dropped category is emptied and its row
  kept, because `Project.category` is `on_delete=SET_NULL` and draft and
  pending projects still point at it without ever appearing in a report. An
  emptied category vanishes from the UI on its own: both `ListingTabs` and
  `CategoryRowsSection` filter on `project_count > 0`, which counts only
  approved projects.

## Common failures

| Failure | Fix |
|---|---|
| Categories invented from the titles alone | Read the descriptions; the titles are Icelandic brand names |
| A "Other / Misc" bucket for the awkward 15% | Either the taxonomy is missing a real category, or those projects go in `unplaced` with reasons |
| Grouping by tech stack ("Next.js apps", "Python tools") | Tags already do that. Group by purpose and audience |
| Every project rehomed | Churn breaks URLs. Keep what works; justify each move |
| Report written, check never run | The check is the only thing standing between a report and a hallucinated project list. Run it |
| Export taken from a local backend, report checked against production | Both steps need the same `--api-url`, or the check reports differences that are only your seed data |
| Warnings shrugged off | Fix the grouping or answer them in `observations` |
| Hand-written summary instead of the rendered diff | Summaries drift from the report they describe. Run `diff` and paste it |
