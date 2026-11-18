import { describe, expect, it } from "vitest";

import {
  PROJECT_IMPORT_FORMAT,
  buildProjectImportPrompt,
  parseProjectImport,
  type CurrentListing,
  type ImportTagGroup,
} from "./project-import";

const TAG_GROUPS: ImportTagGroup[] = [
  {
    category: "Type",
    tags: [
      { id: "t-oss", name: "Open source", slug: "open-source" },
      { id: "t-saas", name: "SaaS", slug: "saas" },
    ],
  },
  {
    category: "Stack",
    tags: [{ id: "t-py", name: "Python", slug: "python" }],
  },
];

const VALID = {
  format: PROJECT_IMPORT_FORMAT,
  website_url: "https://example.is",
  title: "Example",
  tagline: "Does a thing",
  description: "# Example\n\nIt does a thing.",
  tags: ["open source", "python"],
};

const CURRENT: CurrentListing = {
  website_url: "https://old.example.is",
  title: "Old name",
  tagline: "What it used to say",
  description: "A short note.",
  tags: ["SaaS"],
};

function parse(input: unknown, groups = TAG_GROUPS) {
  const text = typeof input === "string" ? input : JSON.stringify(input);
  return parseProjectImport(text, groups);
}

describe("parseProjectImport", () => {
  it("maps a valid document to form fields and tag ids", () => {
    const result = parse(VALID);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.project).toEqual({
      website_url: "https://example.is",
      title: "Example",
      tagline: "Does a thing",
      description: "# Example\n\nIt does a thing.",
      tag_ids: ["t-oss", "t-py"],
    });
    expect(result.matchedTags.map((t) => t.name)).toEqual(["Open source", "Python"]);
    expect(result.warnings).toEqual([]);
  });

  it("accepts JSON wrapped in a code fence with prose around it", () => {
    const text = `Here you go!\n\n\`\`\`json\n${JSON.stringify(VALID, null, 2)}\n\`\`\`\n\nLet me know if you want changes.`;
    expect(parse(text).ok).toBe(true);
  });

  it("accepts a document without the format key", () => {
    const rest: Record<string, unknown> = { ...VALID };
    delete rest.format;
    expect(parse(rest).ok).toBe(true);
  });

  it("matches tags by slug too, and de-duplicates", () => {
    const result = parse({ ...VALID, tags: ["SAAS", "saas", "Open Source"] });
    expect(result.ok && result.project.tag_ids).toEqual(["t-saas", "t-oss"]);
  });

  it("leaves tags out when none match, so the current ones are kept", () => {
    const result = parse({ ...VALID, tags: ["Blockchain"] });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.project.tag_ids).toBeUndefined();
    expect(result.warnings).toContainEqual({ code: "unknownTag", value: "Blockchain" });
  });

  it("skips unknown tags with a warning instead of failing", () => {
    const result = parse({ ...VALID, tags: ["Python", "Blockchain"] });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.project.tag_ids).toEqual(["t-py"]);
    expect(result.warnings).toContainEqual({ code: "unknownTag", value: "Blockchain" });
  });

  it("warns about keys it does not know", () => {
    const result = parse({ ...VALID, github_url: "https://github.com/x/y" });
    expect(result.ok && result.warnings).toContainEqual({
      code: "unknownField",
      value: "github_url",
    });
  });

  it("trims strings and drops empty fields, which then keep their current value", () => {
    const result = parse({ website_url: " https://example.is ", title: "  ", tagline: " Hi " });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.project).toEqual({
      website_url: "https://example.is",
      tagline: "Hi",
    });
  });

  it("accepts a reply that only changes some fields", () => {
    const result = parse({ description: "Rewritten." });
    expect(result.ok && result.project).toEqual({ description: "Rewritten." });
  });

  it.each([
    ["", "noJson"],
    ["no braces at all", "noJson"],
    ["{ not json }", "invalidJson"],
    ["[1, 2]", "noJson"],
  ])("rejects %j as %s", (text, code) => {
    const result = parse(text);
    expect(result.ok).toBe(false);
    expect(!result.ok && result.errors[0].code).toBe(code);
  });

  it("rejects another format version", () => {
    const result = parse({ ...VALID, format: "naglasupan.project/v2" });
    expect(!result.ok && result.errors).toEqual([
      { code: "unsupportedFormat", value: "naglasupan.project/v2" },
    ]);
  });

  it("refuses a website_url that isn't http(s)", () => {
    const result = parse({ ...VALID, website_url: "javascript:alert(1)" });
    expect(!result.ok && result.errors).toEqual([
      { code: "invalidUrl", field: "website_url" },
    ]);
  });

  it("reports every over-long field at once", () => {
    const result = parse({ ...VALID, title: "x".repeat(101), tagline: "y".repeat(201) });
    expect(!result.ok && result.errors).toEqual([
      { code: "tooLong", field: "title", max: 100, length: 101 },
      { code: "tooLong", field: "tagline", max: 200, length: 201 },
    ]);
  });

  it("rejects wrong types", () => {
    const result = parse({ ...VALID, title: 5, tags: "Python" });
    expect(!result.ok && result.errors).toEqual([
      { code: "wrongType", field: "title" },
      { code: "wrongType", field: "tags" },
    ]);
  });
});

describe("buildProjectImportPrompt", () => {
  it("names the format, the limits and every tag by category", () => {
    const prompt = buildProjectImportPrompt(TAG_GROUPS, CURRENT);
    expect(prompt).toContain(PROJECT_IMPORT_FORMAT);
    expect(prompt).toContain("100");
    expect(prompt).toContain("200");
    expect(prompt).toContain("Type: Open source, SaaS");
    expect(prompt).toContain("Stack: Python");
  });

  it("tells the assistant to leave tags empty when none are known", () => {
    const prompt = buildProjectImportPrompt([], CURRENT);
    expect(prompt).toContain('"tags": []');
  });

  it("carries the current listing for the assistant to improve", () => {
    const prompt = buildProjectImportPrompt(TAG_GROUPS, {
      ...CURRENT,
      description: "Line one.\n\n```sh\nmake\n```",
    });
    expect(prompt).toContain('"title": "Old name"');
    expect(prompt).toContain('"website_url": "https://old.example.is"');
    expect(prompt).toContain('"tags": [\n    "SaaS"\n  ]');
    // Newlines are escaped inside the JSON string, so a fence in the
    // description can't close the prompt's own fence early.
    expect(prompt).toContain("Line one.\\n\\n```sh");
  });

  it("produces an example that its own parser accepts", () => {
    const prompt = buildProjectImportPrompt(TAG_GROUPS, CURRENT);
    const result = parseProjectImport(prompt, TAG_GROUPS);
    expect(result.ok).toBe(true);
  });
});
