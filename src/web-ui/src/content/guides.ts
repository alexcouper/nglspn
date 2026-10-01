import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

export type GuideSection = {
  id: string;
  title: string;
  body: string;
};

export type Guide = {
  slug: string;
  title: string;
  description: string;
  summary: string;
  kind: "hub" | "spoke";
  parent?: string;
  updated: string;
  sections: GuideSection[];
  related: string[];
  action: { href: string; label: string };
};

// Content lives beside this file, one directory per guide:
//
//   guides/<hub>/{en.md,is.md,structure.json}
//   guides/<hub>/<spoke>/{en.md,is.md,structure.json}
//
// The directory tree is the hub/spoke graph, so `kind` and `parent` are read
// from the layout rather than restated in structure.json. Everything a reader
// sees is in the markdown; structure.json holds only what prose cannot carry.
const CONTENT_DIR = path.join(process.cwd(), "src/content/guides");

const LANGUAGES = ["en", "is"] as const;
type Language = (typeof LANGUAGES)[number];

type Structure = {
  order: number;
  updated: string;
  related: string[];
  action: { href: string };
};

function fail(file: string, problem: string): never {
  throw new Error(`${path.relative(CONTENT_DIR, file)}: ${problem}`);
}

function subdirectories(dir: string): string[] {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);
}

function readStructure(slug: string): Structure {
  const file = path.join(CONTENT_DIR, slug, "structure.json");
  let parsed: unknown;
  try {
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    fail(file, error instanceof Error ? error.message : String(error));
  }
  const structure = parsed as Partial<Structure>;
  if (typeof structure.order !== "number") fail(file, 'needs a numeric "order"');
  if (typeof structure.updated !== "string") fail(file, 'needs an "updated" date, e.g. "2026-09-29"');
  if (!Array.isArray(structure.related)) fail(file, 'needs a "related" array of guide slugs');
  if (typeof structure.action?.href !== "string") fail(file, 'needs "action": { "href": "/somewhere" }');
  return structure as Structure;
}

// Guides are listed hub-first, each hub followed by its own spokes, with
// siblings in the `order` their structure.json gives them.
function slugsInOrder(): string[] {
  const byOrder = (a: { order: number }, b: { order: number }) => a.order - b.order;
  return subdirectories(CONTENT_DIR)
    .map((hub) => ({ slug: hub, order: readStructure(hub).order }))
    .sort(byOrder)
    .flatMap((hub) => [
      hub.slug,
      ...subdirectories(path.join(CONTENT_DIR, hub.slug))
        .map((spoke) => ({ slug: `${hub.slug}/${spoke}`, order: readStructure(`${hub.slug}/${spoke}`).order }))
        .sort(byOrder)
        .map((spoke) => spoke.slug),
    ]);
}

// Section anchors are shared across languages, so each heading carries its own
// id: `## Heading text {#anchor}`. Fenced blocks are skipped so a `##` inside
// one never starts a section.
function parseSections(markdown: string, file: string): GuideSection[] {
  const sections: GuideSection[] = [];
  let fenced = false;
  let body: string[] = [];

  const closeSection = () => {
    const section = sections.at(-1);
    if (section) section.body = body.join("\n").trim();
    body = [];
  };

  for (const line of markdown.split("\n")) {
    if (/^\s{0,3}(```|~~~)/.test(line)) fenced = !fenced;
    const heading = fenced ? null : /^##\s+(.*?)\s*$/.exec(line);
    if (!heading) {
      if (sections.length === 0 && line.trim()) {
        fail(file, `"${line.trim()}" appears before the first "## " heading`);
      }
      body.push(line);
      continue;
    }
    closeSection();
    const anchored = /^(.*?)\s*\{#([a-z0-9-]+)\}$/.exec(heading[1]);
    if (!anchored) fail(file, `heading "${heading[1]}" needs an anchor: "## ${heading[1]} {#an-id}"`);
    if (sections.some((section) => section.id === anchored[2])) {
      fail(file, `two sections share the anchor "{#${anchored[2]}}"`);
    }
    sections.push({ id: anchored[2], title: anchored[1], body: "" });
  }
  closeSection();

  if (sections.length === 0) fail(file, 'has no sections; each one starts with "## Heading {#an-id}"');
  return sections;
}

function readGuide(slug: string, language: Language): Guide {
  const file = path.join(CONTENT_DIR, slug, `${language}.md`);
  if (!fs.existsSync(file)) fail(file, `missing; every guide needs ${LANGUAGES.join(" and ")}`);
  const { data, content } = matter(fs.readFileSync(file, "utf8"));
  for (const key of ["title", "description", "summary", "action"] as const) {
    if (typeof data[key] !== "string" || !data[key].trim()) fail(file, `needs a "${key}" in its frontmatter`);
  }
  const structure = readStructure(slug);
  const parent = slug.includes("/") ? slug.slice(0, slug.lastIndexOf("/")) : undefined;
  return {
    slug,
    kind: parent ? "spoke" : "hub",
    ...(parent ? { parent } : {}),
    title: data.title,
    description: data.description,
    summary: data.summary,
    updated: structure.updated,
    related: structure.related,
    action: { href: structure.action.href, label: data.action },
    sections: parseSections(content, file),
  };
}

function loadGuides(language: Language): Guide[] {
  return slugsInOrder().map((slug) => readGuide(slug, language));
}

export const guides: Guide[] = loadGuides("en");
export const icelandicGuides: Guide[] = loadGuides("is");

// A language switch keeps the reader on the same section, so the anchors have
// to line up. Catch a drifting translation here rather than in a dead link.
guides.forEach((guide, index) => {
  const anchors = (entry: Guide) => entry.sections.map((section) => section.id).join(", ");
  if (anchors(icelandicGuides[index]) !== anchors(guide)) {
    throw new Error(
      `${guide.slug}: en.md and is.md disagree on sections — "${anchors(guide)}" vs "${anchors(icelandicGuides[index])}"`,
    );
  }
});
