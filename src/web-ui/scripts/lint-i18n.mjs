#!/usr/bin/env node
// Scan .ts/.tsx under src/ and verify every t("key") call references a key that
// exists in src/messages/en.json. Resolves namespaces from useTranslations("ns").

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const srcDir = path.join(root, "src");
const enJsonPath = path.join(srcDir, "messages", "en.json");

const en = JSON.parse(fs.readFileSync(enJsonPath, "utf-8"));

function flatten(obj, prefix = "") {
  const out = new Set();
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      for (const x of flatten(v, full)) out.add(x);
    } else if (typeof v === "string") {
      out.add(full);
    }
  }
  return out;
}

const knownKeys = flatten(en);

function walk(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (/\.(tsx?|mts|cts)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) {
      results.push(full);
    }
  }
  return results;
}

const useTranslationsRe = /useTranslations\(\s*["']([^"']+)["']\s*\)/g;
const tCallRe = /\bt\(\s*["']([^"']+)["']\s*/g;

const problems = [];

for (const file of walk(srcDir)) {
  const contents = fs.readFileSync(file, "utf-8");
  const namespaces = [];
  for (const m of contents.matchAll(useTranslationsRe)) {
    namespaces.push(m[1]);
  }
  for (const m of contents.matchAll(tCallRe)) {
    const sub = m[1];
    if (namespaces.length === 0) {
      if (!knownKeys.has(sub)) {
        problems.push({ file, key: sub, hint: "unknown key (no namespace in scope)" });
      }
      continue;
    }
    const resolvedForms = namespaces.map((ns) => `${ns}.${sub}`);
    if (!resolvedForms.some((k) => knownKeys.has(k))) {
      problems.push({
        file,
        key: sub,
        hint: `none of ${resolvedForms.join(", ")} exist in en.json`,
      });
    }
  }
}

if (problems.length === 0) {
  process.exit(0);
}

for (const p of problems) {
  console.error(`[i18n-lint] ${path.relative(root, p.file)}: ${p.key} — ${p.hint}`);
}
console.error(
  `\n${problems.length} i18n problem(s) found. Add the missing keys to src/messages/en.json or remove the t() call.`,
);
process.exit(1);
