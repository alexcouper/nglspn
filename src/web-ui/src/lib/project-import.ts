/**
 * The `naglasupan.project/v1` format: what an AI assistant hands back so a
 * project's listing can be rewritten in one go on its edit page, instead of
 * field by field.
 *
 * The site writes the prompt (so the assistant sees the current listing, the
 * real limits and the real tag list) and reads the reply. Parsing is forgiving about wrapping —
 * code fences, prose around the JSON — and strict about content: limits mirror
 * `apps/projects/models.py`, and a different `format` version is refused
 * rather than half-read.
 *
 * v1 covers only the fields a page renders. The API also takes
 * long_description, github_url, demo_url and tech_stack, but nothing shows
 * them; asking an assistant to fill them would store text nobody sees.
 */

export const PROJECT_IMPORT_FORMAT = "naglasupan.project/v1";

export const PROJECT_IMPORT_LIMITS = {
  website_url: 2083,
  title: 100,
  tagline: 200,
} as const;

const STRING_FIELDS = ["website_url", "title", "tagline", "description"] as const;
type StringField = (typeof STRING_FIELDS)[number];
const KNOWN_KEYS = new Set<string>(["format", "tags", ...STRING_FIELDS]);

export interface ImportTag {
  id: string;
  name: string;
  slug: string;
  color?: string | null;
}

export interface ImportTagGroup {
  category: string;
  tags: ImportTag[];
}

/**
 * The fields the reply sets. A field left out (or empty) means "keep what's
 * there", and so does a tag list in which no name matched: replacing the
 * project's tags with nothing because the assistant invented every name would
 * lose data the maker chose.
 */
export interface ImportedProject {
  website_url?: string;
  title?: string;
  tagline?: string;
  description?: string;
  tag_ids?: string[];
}

/** What the listing says now, as the prompt shows it to the assistant. */
export interface CurrentListing {
  website_url: string;
  title: string;
  tagline: string;
  description: string;
  tags: string[];
}

export type ImportError =
  | { code: "noJson" }
  | { code: "invalidJson" }
  | { code: "unsupportedFormat"; value: string }
  | { code: "wrongType"; field: StringField | "tags" | "format" }
  | { code: "invalidUrl"; field: "website_url" }
  | { code: "tooLong"; field: StringField; max: number; length: number };

export type ImportWarning =
  | { code: "unknownTag"; value: string }
  | { code: "unknownField"; value: string };

export type ImportResult =
  | {
      ok: true;
      project: ImportedProject;
      matchedTags: ImportTag[];
      warnings: ImportWarning[];
    }
  | { ok: false; errors: ImportError[] };

/** The JSON object in an assistant's reply: a ```json fence if there is one, else the outermost braces. */
function extractJsonText(text: string): string | null {
  const fenced = text.match(/```(?:json)?\s*\n([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1] : text;
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start === -1 || end <= start) return null;
  return candidate.slice(start, end + 1);
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function parseProjectImport(text: string, tagGroups: ImportTagGroup[]): ImportResult {
  const jsonText = extractJsonText(text);
  if (jsonText === null) return { ok: false, errors: [{ code: "noJson" }] };

  let data: unknown;
  try {
    data = JSON.parse(jsonText);
  } catch {
    return { ok: false, errors: [{ code: "invalidJson" }] };
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return { ok: false, errors: [{ code: "noJson" }] };
  }
  const doc = data as Record<string, unknown>;

  if (doc.format !== undefined) {
    if (typeof doc.format !== "string") {
      return { ok: false, errors: [{ code: "wrongType", field: "format" }] };
    }
    if (doc.format !== PROJECT_IMPORT_FORMAT) {
      return { ok: false, errors: [{ code: "unsupportedFormat", value: doc.format }] };
    }
  }

  const errors: ImportError[] = [];
  const warnings: ImportWarning[] = [];
  const strings: Partial<Record<StringField, string>> = {};

  for (const field of STRING_FIELDS) {
    const raw = doc[field];
    if (raw === undefined || raw === null) continue;
    if (typeof raw !== "string") {
      errors.push({ code: "wrongType", field });
      continue;
    }
    const value = raw.trim();
    if (!value) continue;
    const max = PROJECT_IMPORT_LIMITS[field as keyof typeof PROJECT_IMPORT_LIMITS];
    if (max !== undefined && value.length > max) {
      errors.push({ code: "tooLong", field, max, length: value.length });
      continue;
    }
    strings[field] = value;
  }

  if (strings.website_url !== undefined && !isHttpUrl(strings.website_url)) {
    errors.push({ code: "invalidUrl", field: "website_url" });
  }

  const matchedTags: ImportTag[] = [];
  const rawTags = doc.tags;
  if (rawTags !== undefined && rawTags !== null) {
    if (!Array.isArray(rawTags) || rawTags.some((t) => typeof t !== "string")) {
      errors.push({ code: "wrongType", field: "tags" });
    } else {
      const byKey = new Map<string, ImportTag>();
      for (const tag of tagGroups.flatMap((g) => g.tags)) {
        byKey.set(tag.name.toLowerCase(), tag);
        byKey.set(tag.slug.toLowerCase(), tag);
      }
      for (const name of rawTags as string[]) {
        const tag = byKey.get(name.trim().toLowerCase());
        if (!tag) {
          warnings.push({ code: "unknownTag", value: name });
        } else if (!matchedTags.includes(tag)) {
          matchedTags.push(tag);
        }
      }
    }
  }

  for (const key of Object.keys(doc)) {
    if (!KNOWN_KEYS.has(key)) warnings.push({ code: "unknownField", value: key });
  }

  if (errors.length > 0) return { ok: false, errors };

  const project: ImportedProject = {};
  if (strings.website_url) project.website_url = strings.website_url;
  if (matchedTags.length > 0) project.tag_ids = matchedTags.map((t) => t.id);
  if (strings.title) project.title = strings.title;
  if (strings.tagline) project.tagline = strings.tagline;
  if (strings.description) project.description = strings.description;

  return { ok: true, project, matchedTags, warnings };
}

/**
 * The prompt a maker gives their assistant. Plain English on purpose — it is
 * input for a model, not UI copy, and the format keys are English anyway.
 *
 * It carries the current listing so the assistant improves it rather than
 * starting from a blank page; a fresh draft simply has empty fields.
 */
export function buildProjectImportPrompt(
  tagGroups: ImportTagGroup[],
  current: CurrentListing,
): string {
  const nonEmpty = tagGroups.filter((g) => g.tags.length > 0);
  const tagSection =
    nonEmpty.length > 0
      ? [
          "Pick 1–5 tags that fit, using ONLY these exact names (grouped by category):",
          "",
          ...nonEmpty.map((g) => `- ${g.category}: ${g.tags.map((t) => t.name).join(", ")}`),
          "",
          "Keep the current tags that still fit. Do not invent tags.",
        ].join("\n")
      : 'No tag list is available, so leave tags empty: "tags": [].';

  const currentJson = JSON.stringify(
    {
      format: PROJECT_IMPORT_FORMAT,
      website_url: current.website_url,
      title: current.title,
      tagline: current.tagline,
      description: current.description,
      tags: current.tags,
    },
    null,
    2,
  );

  return `You are helping me improve my project's listing on Naglasúpan (naglasupan.is), a showcase of things people in Iceland have built.

Below is what the listing says now. Some fields may be empty. Rewrite it so it is clear, specific and alive: fill in what's missing, tighten what's vague, and update anything the material I add after this prompt shows is out of date. Keep every fact that is still true; don't drop information without a reason.

Reply with the COMPLETE improved listing (every field, not just the changes) as ONE JSON object in this exact format, inside a \`\`\`json code block, and nothing else:

\`\`\`json
{
  "format": "${PROJECT_IMPORT_FORMAT}",
  "website_url": "https://example.is",
  "title": "Example",
  "tagline": "One sentence on what it does and for whom",
  "description": "## What it is\\n\\nA few short paragraphs in Markdown.",
  "tags": []
}
\`\`\`

Rules:
- "format": always "${PROJECT_IMPORT_FORMAT}".
- "website_url": the project's public http(s) address. Keep the current one unless the material gives a newer one.
- "title": the project's name, at most ${PROJECT_IMPORT_LIMITS.title} characters. Keep the current name unless it has changed.
- "tagline": one plain sentence, at most ${PROJECT_IMPORT_LIMITS.tagline} characters, no Markdown.
- "description": Markdown, roughly 100–300 words. Say what it is, who it is for, what makes it interesting, and how it was built if that is known. Use short paragraphs and at most a couple of "##" headings. No marketing fluff, no emoji, and do not repeat the tagline word for word.
- "tags": a list of tag names (strings).
- Write in the language the current listing is in (Icelandic or English). If it is empty, use the language of the material I give you.
- Only state facts that are in the current listing or the material. If something is unknown, leave it out rather than guessing.

${tagSection}

The current listing:

\`\`\`json
${currentJson}
\`\`\`

Anything new I want you to take into account (a README, release notes, what has changed) follows below. If nothing follows, improve the listing from what is there.

`;
}
