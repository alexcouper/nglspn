// Mockup plumbing only: the app shell and a few render helpers so each option
// file is just its own layout.
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function shell(active) {
  const tabs = [
    { label: "Latest", key: "latest" },
    { label: "Discover", key: "discover" },
    ...CATEGORIES.map((c) => ({ label: c.name, key: c.slug })),
  ];
  return `
  <div class="nav"><div class="nav-inner"><span class="nav-brand">naglasúpan</span></div></div>
  <div class="tabs"><div class="tabs-inner">
    ${tabs
      .map((t) => `<a class="tab" ${t.key === active ? 'aria-current="page"' : ""}>${esc(t.label)}</a>`)
      .join("")}
    <a class="tabs-cta">Create a project</a>
  </div></div>`;
}

function frame(label, note) {
  return `<div class="frame-label"><b>${esc(label)}</b> &nbsp;<span>${note}</span></div>`;
}

const winBadge = (wins) =>
  wins.length ? `<span class="win">${esc(wins[0])} winner</span>` : "";

// A third of live projects have no tagline. Every option has to say something
// in that space rather than leave a hole, so the fallback is part of the design.
const taglineOr = (p, fallback = "No description yet") =>
  p.tagline ? esc(p.tagline) : `<span style="color:var(--muted-2)">${fallback}</span>`;

function placeholder(seed, cls) {
  const h = [...String(seed)].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  return `<div class="${cls}" style="background:linear-gradient(135deg,hsl(${h} 42% 72%),hsl(${(h + 40) % 360} 46% 58%))"></div>`;
}

// "2026-10-02" -> "2 Oct". Dates are the thing that marks news as news here,
// so they are written the way a person reads them aloud.
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const fmtDate = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
};
