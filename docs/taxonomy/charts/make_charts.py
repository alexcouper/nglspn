# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8", "pandas>=2.0"]
# ///
"""Sankey / alluvial charts for the Naglasupan taxonomy change.

Reads the newest ../<date>-report.json and renders 10 charts into ./out:
  00-overview          every flow from the four old categories to the nine new ones
  01..09-<slug>        the same diagram, one new category at a time, with the
                       projects that landed in it named on the right

Run with: uv run make_charts.py
"""
import collections
import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
for stale in (*OUT.glob("*.png"), *OUT.glob("*.svg")):
    stale.unlink()

CHARTS = []  # (stem, label), in render order, for the index page

# The report is the only source of truth; deriving the frames here rather than
# keeping CSVs alongside means the charts cannot drift from the report.
REPORT = sorted(HERE.parent.glob("*-report.json"))[-1]
report = json.loads(REPORT.read_text())

OLD = {c["slug"]: c["name"] for c in report["current_categories"]}
NEW = {c["slug"]: c["name"] for c in report["proposed_taxonomy"]}

projects = pd.DataFrame([
    {
        "title": p["title"],
        "from_slug": p["current_category_slug"],
        "from_name": OLD.get(p["current_category_slug"]),
        "to_slug": p["proposed_category_slug"],
        "to_name": NEW.get(p["proposed_category_slug"]),
        "moved": int(p["current_category_slug"] != p["proposed_category_slug"]),
        "confidence": p["confidence"],
    }
    for p in report["projects"]
])

counted = collections.Counter(zip(projects.from_slug, projects.to_slug))
flows = pd.DataFrame([
    {"from_slug": a, "from_name": OLD.get(a), "to_slug": b, "to_name": NEW.get(b),
     "n": n}
    for (a, b), n in counted.items()
])

cats = pd.DataFrame(
    [{"side": "old", "order": i, "slug": c["slug"], "name": c["name"], "status": ""}
     for i, c in enumerate(report["current_categories"])]
    + [{"side": "new", "order": i, "slug": c["slug"], "name": c["name"],
        "status": c["status"]}
       for i, c in enumerate(report["proposed_taxonomy"])]
)

# ---------------------------------------------------------------- style ----
BG = "#FAFAF7"
INK = "#111111"
MUTED = "#555555"
FAINT = "#888888"
GREY_NODE = "#C9C7BF"
GREY_RIBBON = "#DCDAD2"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Inter", "Helvetica", "Arial",
                        "DejaVu Sans"],
    "axes.titlecolor": INK,
    "axes.labelcolor": "#333333",
})

# Colour is by SOURCE category: the point of the chart is watching
# Apps & Services come apart, so its ribbons need one identity.
SOURCE_COLORS = {
    "apps-services": "#E8833A",
    "community-public-good": "#1FAE74",
    "developer-tools": "#5046E5",
    "productivity-business": "#B8438C",
}
RIGHT_NODE = "#4A4A46"

OLD_NAME = dict(zip(cats[cats.side == "old"].slug, cats[cats.side == "old"].name))
NEW_NAME = dict(zip(cats[cats.side == "new"].slug, cats[cats.side == "new"].name))
NEW_STATUS = dict(zip(cats[cats.side == "new"].slug, cats[cats.side == "new"].status))

# Both columns are alphabetical. New categories sit above the kept ones so that
# they meet Apps & Services at the top of the left column, which leaves the three
# survivors facing their own left-hand rows and their ribbons running flat.
# This is deliberately NOT the report's display_order — see README.
LEFT_ORDER = sorted(OLD_NAME, key=lambda s: OLD_NAME[s].lower())
RIGHT_ORDER = sorted(NEW_NAME,
                     key=lambda s: (NEW_STATUS[s] == "kept", NEW_NAME[s].lower()))

LEFT_TOTAL = flows.groupby("from_slug").n.sum().to_dict()
RIGHT_TOTAL = flows.groupby("to_slug").n.sum().to_dict()

# ------------------------------------------------------------- geometry ----
Y_TOP, Y_BOT = 0.795, 0.070
LEFT_GAP, RIGHT_GAP = 0.030, 0.018
N_TOTAL = int(flows.n.sum())

# One project is worth the same vertical distance on both sides, so a ribbon
# keeps its thickness end to end.
UNIT = min(
    (Y_TOP - Y_BOT - LEFT_GAP * (len(LEFT_ORDER) - 1)) / N_TOTAL,
    (Y_TOP - Y_BOT - RIGHT_GAP * (len(RIGHT_ORDER) - 1)) / N_TOTAL,
)


def stack(order, totals, gap):
    """Vertical extents per node, top-down, centred in the content band."""
    height = sum(totals[s] for s in order) * UNIT + gap * (len(order) - 1)
    y = Y_BOT + (Y_TOP - Y_BOT - height) / 2 + height
    spans = {}
    for slug in order:
        h = totals[slug] * UNIT
        spans[slug] = (y - h, y)  # (bottom, top)
        y -= h + gap
    return spans


LEFT_SPAN = stack(LEFT_ORDER, LEFT_TOTAL, LEFT_GAP)
RIGHT_SPAN = stack(RIGHT_ORDER, RIGHT_TOTAL, RIGHT_GAP)


def ribbon_offsets():
    """Where each flow attaches on each node, stacked by the opposite order."""
    at = {}
    cursor = {s: LEFT_SPAN[s][1] for s in LEFT_ORDER}
    for src in LEFT_ORDER:
        for dst in RIGHT_ORDER:
            row = flows[(flows.from_slug == src) & (flows.to_slug == dst)]
            if row.empty:
                continue
            h = int(row.n.iloc[0]) * UNIT
            at[(src, dst, "L")] = (cursor[src] - h, cursor[src])
            cursor[src] -= h
    cursor = {s: RIGHT_SPAN[s][1] for s in RIGHT_ORDER}
    for dst in RIGHT_ORDER:
        for src in LEFT_ORDER:
            row = flows[(flows.from_slug == src) & (flows.to_slug == dst)]
            if row.empty:
                continue
            h = int(row.n.iloc[0]) * UNIT
            at[(src, dst, "R")] = (cursor[dst] - h, cursor[dst])
            cursor[dst] -= h
    return at


AT = ribbon_offsets()


def draw_ribbon(ax, x0, x1, y0, y1, color, alpha, z=2):
    """A filled Bezier band from vertical extent y0 on the left to y1 on the right."""
    (b0, t0), (b1, t1) = y0, y1
    cx = (x0 + x1) / 2
    verts = [
        (x0, t0), (cx, t0), (cx, t1), (x1, t1),   # top edge
        (x1, b1), (cx, b1), (cx, b0), (x0, b0),   # bottom edge back
        (x0, t0),
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, alpha=alpha,
                           edgecolor="none", zorder=z))


def draw_sankey(ax, layout, focus=None):
    """The diagram itself. focus=None renders the overview; a slug greys the rest."""
    xl0, xl1, xr0, xr1 = layout["nodes"]

    for _, f in flows.iterrows():
        lit = focus is None or f.to_slug == focus
        stays = f.from_slug == f.to_slug
        color = SOURCE_COLORS[f.from_slug] if lit else GREY_RIBBON
        if not lit:
            alpha = 0.55
        else:
            alpha = 0.30 if stays else 0.62
        draw_ribbon(ax, xl1, xr0,
                    AT[(f.from_slug, f.to_slug, "L")],
                    AT[(f.from_slug, f.to_slug, "R")],
                    color, alpha, z=2 if lit else 1)

    # left nodes + labels
    for slug in LEFT_ORDER:
        b, t = LEFT_SPAN[slug]
        feeds = focus is None or not flows[(flows.from_slug == slug)
                                           & (flows.to_slug == focus)].empty
        color = SOURCE_COLORS[slug] if feeds else GREY_NODE
        ax.add_patch(Rectangle((xl0, b), xl1 - xl0, t - b, facecolor=color,
                               edgecolor="none", zorder=3))
        ax.text(xl0 - 0.012, (b + t) / 2, f"{OLD_NAME[slug]}  ({LEFT_TOTAL[slug]})",
                ha="right", va="center", fontsize=layout["label_fs"],
                color=INK if feeds else FAINT,
                fontweight="bold" if feeds else "normal", zorder=4)

    # right nodes + labels
    for slug in RIGHT_ORDER:
        b, t = RIGHT_SPAN[slug]
        lit = focus is None or slug == focus
        ax.add_patch(Rectangle((xr0, b), xr1 - xr0, t - b,
                               facecolor=RIGHT_NODE if lit else GREY_NODE,
                               edgecolor="none", zorder=3))
        # A category either survives unchanged or it is new to the visitor;
        # how it was arrived at (split, merged, renamed) is report bookkeeping.
        is_new = NEW_STATUS[slug] != "kept"
        ax.text(xr1 + 0.012, (b + t) / 2 + (0.011 if is_new else 0.0),
                f"{NEW_NAME[slug]}  ({RIGHT_TOTAL[slug]})",
                ha="left", va="center", fontsize=layout["label_fs"],
                color=INK if lit else FAINT,
                fontweight="bold" if lit else "normal", zorder=4)
        if is_new:
            ax.text(xr1 + 0.012, (b + t) / 2 - 0.017, "NEW",
                    ha="left", va="center", fontsize=layout["label_fs"] - 3.2,
                    color=MUTED if lit else "#B5B3AB", zorder=4)

    ax.text(xl0 - 0.012, Y_TOP + 0.040, "BEFORE  ·  4 CATEGORIES", ha="right",
            fontsize=layout["label_fs"] - 2, color=FAINT, fontweight="bold")
    ax.text(xr1 + 0.012, Y_TOP + 0.040, "AFTER  ·  9 CATEGORIES", ha="left",
            fontsize=layout["label_fs"] - 2, color=FAINT, fontweight="bold")


def new_figure(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return fig, ax


INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taxonomy change charts</title>
<style>
  :root {
    --bg: #FAFAF7; --ink: #111111; --muted: #555555;
    --faint: #888888; --rule: #E2E0D8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.5 "Helvetica Neue", Inter, Helvetica, Arial, sans-serif;
  }
  header {
    position: sticky; top: 0; z-index: 10;
    background: rgba(250, 250, 247, 0.94); backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--rule); padding: 14px 32px;
  }
  header h1 { margin: 0 0 2px; font-size: 17px; letter-spacing: -0.01em; }
  header p { margin: 0; font-size: 13px; color: var(--faint); }
  nav { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
  nav a {
    font-size: 12.5px; text-decoration: none; color: var(--muted);
    border: 1px solid var(--rule); border-radius: 999px;
    padding: 3px 11px; white-space: nowrap;
  }
  nav a:hover { color: var(--ink); border-color: var(--faint); }
  main { padding: 32px; max-width: 1400px; margin: 0 auto; }
  figure { margin: 0 0 44px; scroll-margin-top: 130px; }
  figcaption {
    display: flex; align-items: baseline; gap: 10px;
    margin-bottom: 10px; font-size: 13px; color: var(--faint);
  }
  figcaption b { color: var(--muted); font-size: 13px; font-weight: 600; }
  figcaption a { color: var(--faint); text-decoration: none; }
  figcaption a:hover { color: var(--ink); text-decoration: underline; }
  img {
    display: block; width: 100%; height: auto;
    border: 1px solid var(--rule); border-radius: 6px;
  }
  footer {
    padding: 0 32px 48px; font-size: 12.5px; color: var(--faint);
    max-width: 1400px; margin: 0 auto;
  }
  code {
    font: 12px ui-monospace, SFMono-Regular, Menlo, monospace;
    background: #F0EEE6; padding: 1px 5px; border-radius: 3px;
  }
</style>
</head>
<body>
<header>
  <h1>Taxonomy change charts</h1>
  <p>Generated from <code>__REPORT__</code></p>
  <nav id="nav"></nav>
</header>

<main id="main"></main>

<footer>
  This page is generated. Rebuild with
  <code>cd docs/taxonomy/charts &amp;&amp; uv run make_charts.py</code>.
</footer>

<script>
  const CHARTS = __CHARTS__;
  const nav = document.getElementById("nav");
  const main = document.getElementById("main");

  for (const [stem, label] of CHARTS) {
    const a = document.createElement("a");
    a.href = "#" + stem;
    a.textContent = label;
    nav.appendChild(a);

    const fig = document.createElement("figure");
    fig.id = stem;

    const cap = document.createElement("figcaption");
    const b = document.createElement("b");
    b.textContent = label;
    const png = document.createElement("a");
    png.href = `out/${stem}.png`;
    png.textContent = "PNG";
    const svg = document.createElement("a");
    svg.href = `out/${stem}.svg`;
    svg.textContent = "SVG";
    cap.append(b, png, svg);

    const img = document.createElement("img");
    img.src = `out/${stem}.png`;
    img.alt = label + " Sankey diagram";
    img.loading = "lazy";

    fig.append(cap, img);
    main.appendChild(fig);
  }
</script>
</body>
</html>
"""


def write_index():
    """Regenerate index.html so its chart list cannot drift from the renders."""
    html = (INDEX_TEMPLATE
            .replace("__REPORT__", REPORT.name)
            .replace("__CHARTS__", json.dumps(CHARTS)))
    (HERE / "index.html").write_text(html)
    print("  index.html")


def save(fig, stem):
    fig.savefig(OUT / f"{stem}.png", dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(OUT / f"{stem}.svg", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  {stem}.png / .svg")


# ------------------------------------------------------------- overview ----
OVERVIEW = {"nodes": (0.222, 0.246, 0.660, 0.684), "label_fs": 11.5}

fig, ax = new_figure((12, 7.6))
draw_sankey(ax, OVERVIEW)
fig.text(0.055, 0.955, "Category Changes", fontsize=23,
         fontweight="bold", color=INK)
moved = int(projects.moved.sum())
fig.text(0.055, 0.917,
         f"{N_TOTAL} projects, 4 categories becoming 9 · {moved} move, "
         f"{N_TOTAL - moved} stay",
         fontsize=12.5, color=MUTED)
fig.text(0.945, 0.022, "naglasupan.is", ha="right", fontsize=10, color=FAINT)
print("rendering:")
save(fig, "00-overview")
CHARTS.append(("00-overview", "Overview"))

# ------------------------------------------- one chart per new category ----
DETAIL = {"nodes": (0.218, 0.240, 0.470, 0.492), "label_fs": 10.5}

for i, slug in enumerate(RIGHT_ORDER, start=1):
    fig, ax = new_figure((12, 7.6))
    draw_sankey(ax, DETAIL, focus=slug)

    members = projects[projects.to_slug == slug]

    fig.text(0.055, 0.955, NEW_NAME[slug], fontsize=23, fontweight="bold", color=INK)

    # ---- project panel ----
    px = 0.735
    ax.plot([px - 0.028, px - 0.028], [0.055, 0.87], color="#E2E0D8",
            linewidth=1.0, zorder=1)
    y = 0.845
    ax.text(px, y, "PROJECTS", fontsize=9.5, color=FAINT, fontweight="bold",
            va="top")
    y -= 0.052
    order = sorted(members.from_slug.unique(),
                   key=lambda s: (s != slug, LEFT_ORDER.index(s)))
    for src in order:
        group = members[members.from_slug == src].sort_values(
            "title", key=lambda c: c.str.lower())
        heading = "Staying" if src == slug else f"From {OLD_NAME[src]}"
        ax.text(px, y, f"{heading}  ({len(group)})", fontsize=9.5,
                color=SOURCE_COLORS[src], fontweight="bold", va="top")
        y -= 0.038
        for title in group.title:
            ax.add_patch(mpatches.Circle((px + 0.007, y - 0.007), 0.0055,
                                         facecolor=SOURCE_COLORS[src],
                                         edgecolor="none", zorder=4))
            ax.text(px + 0.024, y, title, fontsize=10.5, color="#2A2A28",
                    va="top")
            y -= 0.0345
        y -= 0.012

    fig.text(0.945, 0.022, "naglasupan.is", ha="right", fontsize=10, color=FAINT)
    save(fig, f"{i:02d}-{slug}")
    CHARTS.append((f"{i:02d}-{slug}", NEW_NAME[slug]))

write_index()
print(f"\n{len(CHARTS)} charts in {OUT}")
