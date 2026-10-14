import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { RuleTester } from "eslint";
import rule from "./no-hardcoded-ui-strings.mjs";
import { I18N_PENDING_FILES } from "./i18n-pending.mjs";

const webUiRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const tester = new RuleTester({
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
});

const textError = (text) => ({ messageId: "text", data: { text } });
const attributeError = (attribute, text) => ({ messageId: "attribute", data: { attribute, text } });

tester.run("no-hardcoded-ui-strings", rule, {
  valid: [
    { name: "translated text", code: `const a = <p>{t("title")}</p>;` },
    { name: "punctuation only", code: `const a = <span> · </span>;` },
    { name: "ellipsis only", code: `const a = <span>...</span>;` },
    { name: "digits only", code: `const a = <span>{count} / 10</span>;` },
    { name: "explicit space", code: `const a = <p>{t("a")}{" "}{t("b")}</p>;` },
    { name: "non-readable attributes", code: `const a = <a className="btn primary" href="/x" role="button" data-testid="save" />;` },
    { name: "translated attribute", code: `const a = <img alt={t("logoAlt")} />;` },
    { name: "allow-listed text", code: `const a = <span>naglasúpan</span>;`, options: [{ allow: ["naglasúpan"] }] },
    { name: "condition on the left of && is not rendered", code: `const a = <p>{"a" && t("x")}</p>;` },
    { name: "string literal outside JSX", code: `const label = "Save"; const a = <p>{label}</p>;` },
  ],
  invalid: [
    {
      name: "bare text",
      code: `const a = <p>Save changes</p>;`,
      errors: [textError("Save changes")],
    },
    {
      name: "multi-line text is reported collapsed",
      code: `const a = (\n  <p>\n    Save\n    changes\n  </p>\n);`,
      errors: [textError("Save changes")],
    },
    {
      name: "string literal child",
      code: `const a = <p>{"Save"}</p>;`,
      errors: [textError("Save")],
    },
    {
      name: "both branches of a ternary",
      code: `const a = <button>{saving ? "Saving..." : "Save"}</button>;`,
      errors: [textError("Saving..."), textError("Save")],
    },
    {
      name: "template literal child",
      code: "const a = <p>{`Resend in ${n}s`}</p>;",
      errors: [textError("Resend in …s")],
    },
    {
      name: "fallback of ||",
      code: `const a = <p>{name || "Anonymous"}</p>;`,
      errors: [textError("Anonymous")],
    },
    {
      name: "fallback of ??",
      code: `const a = <p>{name ?? "Anonymous"}</p>;`,
      errors: [textError("Anonymous")],
    },
    {
      name: "placeholder attribute",
      code: `const a = <input placeholder="you@example.com" />;`,
      errors: [attributeError("placeholder", "you@example.com")],
    },
    {
      name: "aria-label attribute",
      code: `const a = <button aria-label="Open menu" />;`,
      errors: [attributeError("aria-label", "Open menu")],
    },
    {
      name: "alt attribute",
      code: `const a = <img alt="Project cover" />;`,
      errors: [attributeError("alt", "Project cover")],
    },
    {
      name: "custom prop by suffix",
      code: `const a = <Empty emptyMessage="Nothing here yet" />;`,
      errors: [attributeError("emptyMessage", "Nothing here yet")],
    },
    {
      name: "attribute with a ternary",
      code: `const a = <button title={open ? "Collapse" : "Expand"} />;`,
      errors: [attributeError("title", "Collapse"), attributeError("title", "Expand")],
    },
    {
      name: "allow list is exact, not prefix",
      code: `const a = <span>naglasúpan rocks</span>;`,
      options: [{ allow: ["naglasúpan"] }],
      errors: [textError("naglasúpan rocks")],
    },
  ],
});

describe("i18n pending list", () => {
  it("only names files that still exist, so finished migrations are removed from it", () => {
    const missing = I18N_PENDING_FILES.filter((file) => !existsSync(path.join(webUiRoot, file)));
    expect(missing).toEqual([]);
  });

  it("has no duplicates", () => {
    expect(new Set(I18N_PENDING_FILES).size).toBe(I18N_PENDING_FILES.length);
  });
});

describe("message areas", () => {
  it("every src/i18n/<area>/ directory is imported by messages.ts", async () => {
    const i18nDir = path.join(webUiRoot, "src", "i18n");
    const areas = readdirSync(i18nDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();
    const { messages } = await import("../src/i18n/messages.ts");
    expect(Object.keys(messages).sort()).toEqual(areas);
  });

  it("every area has an en.json", () => {
    const i18nDir = path.join(webUiRoot, "src", "i18n");
    for (const entry of readdirSync(i18nDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      expect(existsSync(path.join(i18nDir, entry.name, "en.json")), `${entry.name}/en.json`).toBe(true);
    }
  });
});
