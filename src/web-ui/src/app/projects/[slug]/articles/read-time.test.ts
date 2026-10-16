import { describe, expect, it } from "vitest";

import { readingMinutes } from "./read-time";

function words(count: number): string {
  return Array.from({ length: count }, (_, i) => `word${i}`).join(" ");
}

describe("readingMinutes", () => {
  it("rounds to the nearest minute at 200 words per minute", () => {
    expect(readingMinutes(words(600))).toBe(3);
    expect(readingMinutes(words(500))).toBe(3);
    expect(readingMinutes(words(480))).toBe(2);
  });

  it("never says less than a minute, however short the article", () => {
    expect(readingMinutes("Three words here.")).toBe(1);
    expect(readingMinutes("")).toBe(1);
  });

  it("does not count a fenced code block as prose", () => {
    const withCode = `${words(200)}\n\n\`\`\`ts\n${words(2000)}\n\`\`\`\n`;

    expect(readingMinutes(withCode)).toBe(1);
  });

  it("counts a link's text but not its url", () => {
    const link = `[${words(200)}](https://example.test/a/very/long/path/indeed)`;

    expect(readingMinutes(link)).toBe(1);
  });

  it("ignores gallery directives and the image syntax inside them", () => {
    const gallery = `${words(200)}\n\n:::gallery\n![a caption](https://example.test/one.jpg)\n![another](https://example.test/two.jpg)\n:::\n`;

    expect(readingMinutes(gallery)).toBe(1);
  });

  it("ignores raw html tags but keeps the text they wrap", () => {
    expect(readingMinutes(`<div class="x">${words(400)}</div>`)).toBe(2);
  });

  it("does not count markdown punctuation as words", () => {
    expect(readingMinutes("## Heading\n\n---\n\n* * *\n\n> quote")).toBe(1);
  });
});
