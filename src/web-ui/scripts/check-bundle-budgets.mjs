#!/usr/bin/env node
// Per-route client-JS size budget, measured from the production build in .next.
//
// Why this exists: a dependency-count check cannot tell 162 lazily-loaded
// packages apart from one 272 kB eager chunk. Bytes on the read path is the
// number that matters, so that is what we guard.
//
// What it measures, per app route:
//   - "<route>"        eager client JS, from page_client-reference-manifest.js
//   - "<route> (lazy)" next/dynamic chunks, from react-loadable-manifest.json
// Sizes are gzip -9 of each chunk, summed. Chunks shared between routes are
// counted once per route on purpose: every route that lists a chunk downloads
// it. CSS is not counted.
//
// gzip -9 per chunk is not what the CDN serves (brotli, and HTTP/2 compresses
// across the stream). It is a stable relative measure, not a prediction of
// bytes on the wire.
//
// Usage: node scripts/check-bundle-budgets.mjs [nextDir] [budgetsFile]

import { gzipSync } from "node:zlib";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const CLIENT_MANIFEST = "page_client-reference-manifest.js";
const LOADABLE_MANIFEST = "react-loadable-manifest.json";
const LAZY_SUFFIX = " (lazy)";

export class BudgetCheckError extends Error {}

/** Every chunk path a client-reference manifest names, deduplicated, JS only. */
export function parseClientReferenceManifest(source) {
  const matches = source.matchAll(/"\/_next\/(static\/chunks\/[^"]+?\.js)"/g);
  return [...new Set([...matches].map((m) => m[1]))];
}

/** Every chunk path a react-loadable manifest names, deduplicated, JS only. */
export function parseLoadableManifest(source) {
  let parsed;
  try {
    parsed = JSON.parse(source);
  } catch (cause) {
    throw new BudgetCheckError(`${LOADABLE_MANIFEST} is not valid JSON: ${cause.message}`);
  }
  const files = Object.values(parsed).flatMap((entry) => entry?.files ?? []);
  return [...new Set(files.filter((f) => f.endsWith(".js")))];
}

/** ".next/server/app/projects/[slug]" -> "/projects/[slug]"; the app root -> "/". */
export function routeIdFromDir(appDir, dir) {
  const rel = path.relative(appDir, dir);
  return rel === "" ? "/" : `/${rel.split(path.sep).join("/")}`;
}

function* walkDirs(root) {
  yield root;
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.isDirectory()) yield* walkDirs(path.join(root, entry.name));
  }
}

/**
 * Walk a built .next directory and return one entry per route (and one per
 * route with lazy chunks), each with its deduplicated chunk list.
 */
export function collectRoutes(nextDir) {
  const appDir = path.join(nextDir, "server", "app");
  if (!existsSync(appDir)) {
    throw new BudgetCheckError(
      `no ${appDir} — expected a production build. Run 'make build-app' first.`,
    );
  }

  const entries = [];
  for (const dir of walkDirs(appDir)) {
    const clientManifest = path.join(dir, CLIENT_MANIFEST);
    if (existsSync(clientManifest)) {
      entries.push({
        name: routeIdFromDir(appDir, dir),
        chunks: parseClientReferenceManifest(readFileSync(clientManifest, "utf8")),
      });
    }
    const loadableManifest = path.join(dir, "page", LOADABLE_MANIFEST);
    if (existsSync(loadableManifest)) {
      const chunks = parseLoadableManifest(readFileSync(loadableManifest, "utf8"));
      if (chunks.length > 0) {
        entries.push({ name: routeIdFromDir(appDir, dir) + LAZY_SUFFIX, chunks });
      }
    }
  }

  if (entries.length === 0) {
    throw new BudgetCheckError(
      `found no ${CLIENT_MANIFEST} under ${appDir}. Either the build is not a ` +
        `production build, or Next changed its manifest layout and this script ` +
        `needs updating — refusing to report a passing budget off an empty measurement.`,
    );
  }
  return entries.sort((a, b) => a.name.localeCompare(b.name));
}

/** gzip -9 size of a chunk, cached: the same chunk appears in many routes. */
function makeSizer(nextDir) {
  const cache = new Map();
  return (chunk) => {
    if (cache.has(chunk)) return cache.get(chunk);
    const file = path.join(nextDir, chunk);
    if (!existsSync(file) || !statSync(file).isFile()) {
      throw new BudgetCheckError(
        `manifest names ${chunk} but ${file} does not exist. The build is ` +
          `incomplete or stale — run 'make build-app' and try again.`,
      );
    }
    const size = gzipSync(readFileSync(file), { level: 9 }).length;
    cache.set(chunk, size);
    return size;
  };
}

export function measureRoutes(nextDir) {
  const sizeOf = makeSizer(nextDir);
  return collectRoutes(nextDir).map((entry) => ({
    ...entry,
    bytes: entry.chunks.reduce((sum, chunk) => sum + sizeOf(chunk), 0),
  }));
}

/**
 * Compare measured routes against budgets. Returns { rows, failures }.
 * A budget key that matches no route, or matches a route measuring zero bytes,
 * is a failure: it means the check has stopped measuring what it claims to.
 */
export function evaluateBudgets(measured, budgets) {
  if (!Object.hasOwn(budgets, "*")) {
    throw new BudgetCheckError(
      `budgets file has no "*" default. Without it a new route ships unguarded.`,
    );
  }

  const rows = measured.map((entry) => {
    const explicit = Object.hasOwn(budgets, entry.name);
    return {
      ...entry,
      limit: explicit ? budgets[entry.name] : budgets["*"],
      matchedBy: explicit ? entry.name : "*",
    };
  });

  const failures = rows
    .filter((row) => row.bytes > row.limit)
    .map(
      (row) =>
        `${row.name}: ${fmt(row.bytes)} gz exceeds its ${fmt(row.limit)} budget ` +
        `(matched by "${row.matchedBy}") across ${row.chunks.length} chunk(s)`,
    );

  const measuredByName = new Map(rows.map((row) => [row.name, row]));
  for (const name of Object.keys(budgets)) {
    if (name === "*") continue;
    const row = measuredByName.get(name);
    if (row === undefined) {
      failures.push(
        `${name}: has a budget but no such route was measured. Rename or remove ` +
          `the entry in bundle-budgets.json — a stale budget guards nothing.`,
      );
    } else if (row.bytes === 0) {
      failures.push(
        `${name}: has a budget but measured 0 B. Its manifest named no JS chunks, ` +
          `which almost certainly means the manifest layout changed.`,
      );
    }
  }

  return { rows, failures };
}

function fmt(bytes) {
  return `${(bytes / 1000).toFixed(1)} kB`;
}

function printTable(rows) {
  const sorted = [...rows].sort((a, b) => b.bytes - a.bytes);
  const nameWidth = Math.max(5, ...sorted.map((r) => r.name.length));
  const header = `${"route".padEnd(nameWidth)}  ${"gzip".padStart(9)}  ${"budget".padStart(9)}`;
  console.log(header);
  console.log("-".repeat(header.length));
  for (const row of sorted) {
    const flag = row.bytes > row.limit ? "  OVER" : "";
    console.log(
      `${row.name.padEnd(nameWidth)}  ${fmt(row.bytes).padStart(9)}  ` +
        `${fmt(row.limit).padStart(9)}${flag}`,
    );
  }
}

export function main(argv = []) {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const nextDir = path.resolve(argv[0] ?? path.join(here, "..", ".next"));
  const budgetsFile = path.resolve(argv[1] ?? path.join(here, "..", "bundle-budgets.json"));

  const budgets = JSON.parse(readFileSync(budgetsFile, "utf8"));
  const { rows, failures } = evaluateBudgets(measureRoutes(nextDir), budgets);
  printTable(rows);

  if (failures.length === 0) {
    console.log(`\nAll ${rows.length} route entries are within budget.`);
    return 0;
  }
  console.error("\nERROR: bundle budget exceeded:");
  for (const failure of failures) console.error(`  - ${failure}`);
  console.error(
    "\n       Find what grew (a new eager import is the usual cause) and fix it,\n" +
      `       or raise the number in ${path.relative(process.cwd(), budgetsFile)} in the same\n` +
      "       commit so the trade-off shows up in review.",
  );
  return 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (error) {
    if (error instanceof BudgetCheckError) {
      console.error(`ERROR: bundle budget check could not run.\n       ${error.message}`);
      process.exit(1);
    }
    throw error;
  }
}
