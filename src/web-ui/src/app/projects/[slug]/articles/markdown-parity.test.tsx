import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import rehypePrismPlus from "rehype-prism-plus";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  articleAllowedSpanClasses,
  articleSanitizeSchema,
} from "./sanitize-schema";

// Parity verification for the GFM subset enabled in MDXEditor (tablePlugin,
// listsPlugin, linkPlugin, imagePlugin) plus the raw-HTML constructs we let
// through rehype-raw. MDXEditor writes back idiomatic markdown / HTML for
// each construct; this test checks that the read-page pipeline reads them
// back the same way users will see them.
//
// We assert on rendered HTML structure (tags + key text) rather than exact
// strings so whitespace / attribute ordering noise doesn't cause churn.

// Markdown-only pipeline (what we used pre-rehype-raw). Kept for the pure-GFM
// constructs so we can tell if a regression is in remark or in rehype.
function renderMarkdown(markdown: string): string {
  return renderToStaticMarkup(
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>,
  );
}

// Full read-page pipeline: GFM + rehype-raw + sanitize. This is what users
// actually see.
function renderArticle(markdown: string): string {
  return renderToStaticMarkup(
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[
        rehypeRaw,
        [rehypePrismPlus, { ignoreMissing: true }],
        [rehypeSanitize, articleSanitizeSchema],
      ]}
    >
      {markdown}
    </ReactMarkdown>,
  );
}

// The same pipeline with sanitisation removed, so a test can tell "the
// highlighter never produced this class" from "sanitisation threw it away".
function renderArticleUnsanitized(markdown: string): string {
  return renderToStaticMarkup(
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw, [rehypePrismPlus, { ignoreMissing: true }]]}
    >
      {markdown}
    </ReactMarkdown>,
  );
}

function classNamesIn(html: string): Set<string> {
  const names = new Set<string>();
  for (const match of html.matchAll(/class="([^"]*)"/g)) {
    for (const name of match[1].split(/\s+/).filter(Boolean)) names.add(name);
  }
  return names;
}

const render = renderMarkdown;

describe("GFM construct parity (react-markdown + remark-gfm)", () => {
  it("renders a GFM pipe table", () => {
    const html = render(
      "| Header A | Header B |\n| --- | --- |\n| cell 1 | cell 2 |\n",
    );
    expect(html).toContain("<table>");
    expect(html).toContain("<thead>");
    expect(html).toContain("<th>Header A</th>");
    expect(html).toContain("<td>cell 1</td>");
  });

  it("renders strikethrough", () => {
    const html = render("This is ~~struck~~ text.");
    expect(html).toContain("<del>struck</del>");
  });

  it("renders task list items", () => {
    const html = render("- [ ] todo\n- [x] done\n");
    expect(html).toContain('type="checkbox"');
    expect(html).toMatch(/checked/);
  });

  it("renders autolinks", () => {
    const html = render("Visit https://example.com today.");
    expect(html).toContain('<a href="https://example.com">');
  });

  it("renders images as <img> with alt text", () => {
    const html = render("![alt text](https://example.com/x.png)");
    expect(html).toContain('<img src="https://example.com/x.png"');
    expect(html).toContain('alt="alt text"');
  });

  it("renders ordered and unordered lists", () => {
    const ul = render("- one\n- two\n");
    expect(ul).toContain("<ul>");
    expect(ul).toContain("<li>one</li>");

    const ol = render("1. first\n2. second\n");
    expect(ol).toContain("<ol>");
    expect(ol).toContain("<li>first</li>");
  });

  it("renders inline links", () => {
    const html = render("Check the [docs](https://example.com/docs).");
    expect(html).toContain('<a href="https://example.com/docs">docs</a>');
  });

  it("renders a blockquote, including one spanning several lines", () => {
    expect(render("> quoted\n")).toContain("<blockquote>");

    const multiline = render("> first line\n> second line\n");
    expect(multiline).toContain("<blockquote>");
    expect(multiline).toContain("first line");
    expect(multiline).toContain("second line");
  });

  it("keeps blockquotes through sanitisation", () => {
    expect(renderArticle("> quoted\n")).toContain("<blockquote>");
  });
});

describe("Raw HTML round-trip (rehype-raw + sanitize)", () => {
  it("renders the MDXEditor-emitted <img> tag", () => {
    // This is the exact shape MDXEditor's image plugin serializes back.
    const html = renderArticle(
      '<img height="324" width="580" src="http://example.com/x.jpg" />',
    );
    expect(html).toContain('<img');
    expect(html).toContain('src="http://example.com/x.jpg"');
    expect(html).toContain('width="580"');
    expect(html).toContain('height="324"');
  });

  it("renders the broadcast-style centered image wrapper", () => {
    const html = renderArticle(
      '<div align="center">\n\n<img src="http://example.com/x.jpg" alt="x" />\n\n</div>',
    );
    expect(html).toContain('<div align="center">');
    expect(html).toContain('<img');
    expect(html).toContain('src="http://example.com/x.jpg"');
  });

  it("strips disallowed tags like <script>", () => {
    const html = renderArticle(
      'before<script>alert(1)</script>after',
    );
    expect(html).not.toContain("<script");
    expect(html).not.toContain("alert(1)");
    expect(html).toContain("before");
    expect(html).toContain("after");
  });

  it("strips the style attribute (not in allowlist)", () => {
    const html = renderArticle(
      '<img src="http://example.com/x.jpg" style="background:url(javascript:1)" />',
    );
    expect(html).toContain('<img');
    expect(html).not.toContain("style=");
    expect(html).not.toContain("javascript");
  });

  it("strips javascript: URLs from img src", () => {
    const html = renderArticle(
      '<img src="javascript:alert(1)" alt="x" />',
    );
    expect(html).not.toContain("javascript:");
  });

  it("strips on* event handlers", () => {
    const html = renderArticle(
      '<img src="http://example.com/x.jpg" onerror="alert(1)" />',
    );
    expect(html).not.toContain("onerror");
    expect(html).not.toContain("alert(1)");
  });
});

describe("Code blocks (rehype-prism-plus + sanitize)", () => {
  it("renders inline code as <code>", () => {
    const html = renderArticle("Try `npm test` first.");
    expect(html).toContain("<code");
    expect(html).toContain("npm test");
  });

  it("renders a fenced code block wrapped in <pre><code>", () => {
    const html = renderArticle(
      "```ts\nconst x = 1;\n```\n",
    );
    expect(html).toContain("<pre");
    expect(html).toContain("<code");
    expect(html).toContain("const");
  });

  it("preserves the language- class on fenced code blocks", () => {
    const html = renderArticle(
      "```js\nconst x = 1;\n```\n",
    );
    // rehype-prism-plus adds `language-js` (and `code-highlight`) to the
    // <code> element. Both are on the sanitiser's class allowlist, so they
    // must survive.
    expect(html).toMatch(/language-js/);
  });

  it("emits Prism token spans inside highlighted code", () => {
    const html = renderArticle(
      "```js\nconst answer = 42;\n```\n",
    );
    // Prism produces <span class="token keyword">const</span>, etc. Both
    // class names are on the sanitiser's allowlist so these survive.
    expect(html).toMatch(/<span class="token/);
  });

  it("falls back gracefully for unknown languages (ignoreMissing)", () => {
    const html = renderArticle(
      "```fictionallang\nfoo bar\n```\n",
    );
    // Should not throw, should still render the code text.
    expect(html).toContain("<pre");
    expect(html).toContain("foo bar");
  });
});

// Fenced samples for every language ArticleEditor.tsx offers in its code-block
// dropdown, chosen to exercise a spread of token types per grammar.
const EDITOR_LANGUAGE_SAMPLES: Record<string, string> = {
  ts: 'const n: number = 1; // note\nclass A { get x() { return `t${n}`; } }\n',
  js: 'const re = /a+/g;\nexport default function f(a = "s") { return a ?? 1; }\n',
  tsx: 'const A = ({ x }: { x: number }) => <div className="a">{x}</div>;\n',
  jsx: 'const A = ({ x }) => <div className="a">{/* c */}{x}</div>;\n',
  python: 'import os\n\n\ndef f(a, *, b="s"):\n    """doc"""\n    return f"{a!r}"  # note\n',
  bash: '#!/usr/bin/env bash\nset -e\nfor f in *.txt; do\n  echo "$f" >&2\ndone\n',
  css: '@media (min-width: 40rem) {\n  .a > b::before { color: #fff !important; }\n}\n',
  html: '<!doctype html>\n<div class="a" data-x="1"><!-- c --><b>t</b></div>\n',
  json: '{"a": [1, true, null], "b": {"c": "s"}}\n',
  md: "# Heading\n\n**bold** and *italic* and `code` and [l](https://e.com)\n\n> quote\n",
  sql: "SELECT COUNT(*) AS n FROM t WHERE a = 'x' AND b IS NOT NULL; -- note\n",
};

function fence(language: string, body: string): string {
  return "```" + language + "\n" + body + "```\n";
}

describe("Code-block class sanitisation", () => {
  it("strips the layout classes a contributor could use to cover the page", () => {
    const html = renderArticle(
      '<span class="fixed inset-0 z-50 bg-white">gotcha</span>',
    );
    expect(html).toContain("gotcha");
    for (const utility of ["fixed", "inset-0", "z-50", "bg-white"]) {
      expect(classNamesIn(html)).not.toContain(utility);
    }
  });

  it("strips layout classes from a raw <pre> too", () => {
    const html = renderArticle(
      '<pre class="fixed inset-0 z-50 bg-white">gotcha</pre>',
    );
    expect(html).toContain("gotcha");
    expect(classNamesIn(html).size).toBe(0);
  });

  it("keeps the classes rehype-prism-plus puts on a highlighted block", () => {
    const html = renderArticle(fence("ts", "const x = 1;\n"));
    expect(html).toContain("language-ts");
    expect(html).toContain("code-highlight");
    expect(html).toContain("code-line");
    expect(html).toContain("token keyword");
  });

  it.each(Object.keys(EDITOR_LANGUAGE_SAMPLES))(
    "drops no highlighter class for a %s block",
    (language) => {
      const markdown = fence(language, EDITOR_LANGUAGE_SAMPLES[language]);
      const emitted = classNamesIn(renderArticleUnsanitized(markdown));
      const survived = classNamesIn(renderArticle(markdown));

      expect(emitted.size).toBeGreaterThan(3);
      expect([...emitted].filter((name) => !survived.has(name))).toEqual([]);
    },
  );

  it("still colours the common tokens of a language the editor cannot produce", () => {
    // Pasted markdown can carry any fence. The allow-list is sized to the
    // editor's languages, so exotic token types of other grammars are dropped
    // — but every token class `article-markdown.css` colours survives.
    const html = renderArticle(
      fence("go", 'package main\n\nfunc main() { // note\n\ts := "x"\n}\n'),
    );
    expect(html).toContain("token keyword");
    expect(html).toContain("token string");
    expect(html).toContain("token comment");
  });

  it("allows no class that could position or size an element", () => {
    const layoutUtilities = [
      "fixed",
      "absolute",
      "sticky",
      "relative",
      "inset-0",
      "top-0",
      "left-0",
      "z-50",
      "bg-white",
      "w-full",
      "h-full",
      "block",
      "inline-block",
      "hidden",
      "opacity-0",
      "pointer-events-none",
    ];
    expect(
      layoutUtilities.filter((name) => articleAllowedSpanClasses.has(name)),
    ).toEqual([]);
  });
});
