import { describe, expect, it } from "vitest";

import {
  PROJECT_IMPORT_FORMAT,
  buildProjectImportPrompt,
  parseProjectImport,
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

function parse(input: unknown, groups = TAG_GROUPS) {
  const text = typeof input === "string" ? input : JSON.stringify(input);
  return parseProjectImport(text, groups);
}

describe("parseProjectImport", () => {
  it("maps a valid document to create fields and tag ids", () => {
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

  it("trims strings and drops empty optional fields", () => {
    const result = parse({ website_url: " https://example.is ", title: "  ", tagline: " Hi " });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.project).toEqual({
      website_url: "https://example.is",
      tagline: "Hi",
      tag_ids: [],
    });
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

  it("requires an http(s) website_url", () => {
    expect(!parse({ ...VALID, website_url: undefined }).ok).toBe(true);
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
    const prompt = buildProjectImportPrompt(TAG_GROUPS);
    expect(prompt).toContain(PROJECT_IMPORT_FORMAT);
    expect(prompt).toContain("100");
    expect(prompt).toContain("200");
    expect(prompt).toContain("Type: Open source, SaaS");
    expect(prompt).toContain("Stack: Python");
  });

  it("tells the assistant to leave tags empty when none are known", () => {
    const prompt = buildProjectImportPrompt([]);
    expect(prompt).toContain('"tags": []');
  });

  it("produces an example that its own parser accepts", () => {
    const prompt = buildProjectImportPrompt(TAG_GROUPS);
    const result = parseProjectImport(prompt, TAG_GROUPS);
    expect(result.ok).toBe(true);
  });
});
