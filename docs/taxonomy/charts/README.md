# Taxonomy change charts

Sankey (alluvial) diagrams of a taxonomy report, for explaining a re-categorisation
to the community. Everything in `out/` is generated — edit `make_charts.py`, not
the images.

```bash
cd docs/taxonomy/charts && uv run make_charts.py
```

Open `index.html` to view all ten at once. It is generated too — the script
rewrites it on every run, and clears stale renders, because chart files are
numbered by column order and renumber whenever that order changes.

The script reads the newest `../<date>-report.json` and writes PNG (220dpi, for
posting) and SVG (for re-styling) into `out/`:

| File | Shows |
|------|-------|
| `00-overview` | Every flow at once: old categories left, new right, ribbon thickness = project count |
| `01`–`09-<slug>` | The same diagram with one new category lit and the rest greyed, naming the projects that landed in it |

Reading the charts:

- **Ribbon colour is the category a project came from**, so a dissolved category
  stays one colour as it fragments across its destinations.
- **Faded ribbons are projects that did not move.** Without that distinction the
  diagram overstates the churn.
- Both columns are alphabetical; on the right, new categories come before kept
  ones so the dissolved category at the top left meets its destinations head-on
  and the three survivors' ribbons run flat. This is **not** the report's
  `proposed_taxonomy` order, which is what `apply_taxonomy` reads as
  `display_order` — so these charts say nothing about the order a visitor will
  meet the categories in on the site.
- Subcategories are not drawn. The report proposes them, but `apply_taxonomy`
  ignores them and nothing in the API or UI models a second level.

Node positions are identical across all ten charts, so a reader learns the layout
once and then only watches the highlight move.
