// Run with: npm run test:scripts   (node --test scripts/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { gzipSync } from "node:zlib";

import {
  BudgetCheckError,
  collectRoutes,
  measureRoutes,
  evaluateBudgets,
  parseClientReferenceManifest,
  parseLoadableManifest,
} from "./check-bundle-budgets.mjs";

/** A throwaway .next tree that looks enough like a real production build. */
function fakeBuild(t) {
  const nextDir = mkdtempSync(path.join(tmpdir(), "bundle-budgets-"));
  t.after(() => rmSync(nextDir, { recursive: true, force: true }));

  return {
    dir: nextDir,

    /** Writes static/chunks/<name>, returns the manifest-relative path. */
    chunk(name, body) {
      const rel = path.join("static", "chunks", name);
      const file = path.join(nextDir, rel);
      mkdirSync(path.dirname(file), { recursive: true });
      writeFileSync(file, body);
      return rel;
    },

    eagerRoute(route, chunkPaths) {
      const dir = path.join(nextDir, "server", "app", route);
      mkdirSync(dir, { recursive: true });
      const clientModules = Object.fromEntries(
        chunkPaths.map((c, i) => [`module-${i}`, { chunks: [`/_next/${c}`] }]),
      );
      writeFileSync(
        path.join(dir, "page_client-reference-manifest.js"),
        `globalThis.__RSC_MANIFEST["/${route}/page"] = ${JSON.stringify({ clientModules })};`,
      );
    },

    lazyRoute(route, files) {
      const dir = path.join(nextDir, "server", "app", route, "page");
      mkdirSync(dir, { recursive: true });
      writeFileSync(
        path.join(dir, "react-loadable-manifest.json"),
        JSON.stringify({ 3866: { id: 3866, files } }),
      );
    },
  };
}

const gzipSize = (body) => gzipSync(Buffer.from(body), { level: 9 }).length;

function rowNamed(rows, name) {
  const row = rows.find((r) => r.name === name);
  assert.ok(row, `no measured entry named ${name}; got ${rows.map((r) => r.name).join(", ")}`);
  return row;
}

function assertFailureMentions(failures, needle) {
  assert.ok(
    failures.some((f) => f.includes(needle)),
    `expected a failure mentioning "${needle}", got: ${JSON.stringify(failures, null, 2)}`,
  );
}

test("client reference manifest parser takes only js chunks, once each", () => {
  const source = `x = {"a":{"chunks":["/_next/static/chunks/a.js","/_next/static/chunks/b.css"]},
                   "b":{"chunks":["/_next/static/chunks/a.js"]}};`;
  assert.deepEqual(parseClientReferenceManifest(source), ["static/chunks/a.js"]);
});

test("loadable manifest parser takes only js chunks, once each", () => {
  const source = JSON.stringify({
    1: { files: ["static/chunks/a.js", "static/chunks/a.css"] },
    2: { files: ["static/chunks/a.js", "static/chunks/b.js"] },
  });
  assert.deepEqual(parseLoadableManifest(source), ["static/chunks/a.js", "static/chunks/b.js"]);
});

test("a manifest naming no chunks measures zero rather than being skipped", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("empty", []);

  const measured = measureRoutes(build.dir);

  assert.equal(rowNamed(measured, "/empty").bytes, 0);
});

test("an empty budget on a route that measured nothing fails loudly", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("empty", []);

  const { failures } = evaluateBudgets(measureRoutes(build.dir), { "*": 1000, "/empty": 1000 });

  assertFailureMentions(failures, "measured 0 B");
});

test("a route over its explicit budget fails with its size and its budget", (t) => {
  const build = fakeBuild(t);
  const big = build.chunk("big.js", "x".repeat(50_000) + Math.random());
  build.eagerRoute("heavy", [big]);

  const { failures } = evaluateBudgets(measureRoutes(build.dir), { "*": 1_000_000, "/heavy": 10 });

  assertFailureMentions(failures, "/heavy");
  assertFailureMentions(failures, "budget");
});

test("a route with no explicit budget is held to the wildcard", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("unlisted", [build.chunk("u.js", "console.log(1)")]);

  const passing = evaluateBudgets(measureRoutes(build.dir), { "*": 1_000_000 });
  const failing = evaluateBudgets(measureRoutes(build.dir), { "*": 1 });

  assert.equal(rowNamed(passing.rows, "/unlisted").matchedBy, "*");
  assert.deepEqual(passing.failures, []);
  assertFailureMentions(failing.failures, "/unlisted");
});

test("a chunk shared by two routes counts once per route", (t) => {
  const build = fakeBuild(t);
  const shared = build.chunk("shared.js", "shared body ".repeat(100));
  build.eagerRoute("one", [shared]);
  build.eagerRoute("two", [shared]);

  const measured = measureRoutes(build.dir);

  const expected = gzipSize("shared body ".repeat(100));
  assert.equal(rowNamed(measured, "/one").bytes, expected);
  assert.equal(rowNamed(measured, "/two").bytes, expected);
});

test("a chunk listed twice within one route counts once", (t) => {
  const build = fakeBuild(t);
  const chunk = build.chunk("dup.js", "duplicated ".repeat(100));
  build.eagerRoute("dup", [chunk, chunk]);

  assert.equal(rowNamed(measureRoutes(build.dir), "/dup").bytes, gzipSize("duplicated ".repeat(100)));
});

test("lazy chunks are reported as a separate entry from the route's eager JS", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("editor", [build.chunk("eager.js", "eager".repeat(100))]);
  build.lazyRoute("editor", ["static/chunks/lazy.js", "static/chunks/lazy.css"]);
  build.chunk("lazy.js", "lazy".repeat(500));

  const measured = measureRoutes(build.dir);

  assert.equal(rowNamed(measured, "/editor").bytes, gzipSize("eager".repeat(100)));
  assert.equal(rowNamed(measured, "/editor (lazy)").bytes, gzipSize("lazy".repeat(500)));
});

test("a build with no manifests at all is an error, not a pass", (t) => {
  const build = fakeBuild(t);
  mkdirSync(path.join(build.dir, "server", "app"), { recursive: true });

  assert.throws(() => collectRoutes(build.dir), BudgetCheckError);
});

test("a missing .next is an error, not a pass", () => {
  assert.throws(
    () => collectRoutes(path.join(tmpdir(), "definitely-not-a-build")),
    /make build-app/,
  );
});

test("a manifest naming a chunk that is not on disk is an error", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("ghost", ["static/chunks/missing.js"]);

  assert.throws(() => measureRoutes(build.dir), /does not exist/);
});

test("a budget for a route that no longer exists is an error", (t) => {
  const build = fakeBuild(t);
  build.eagerRoute("kept", [build.chunk("k.js", "kept")]);

  const { failures } = evaluateBudgets(measureRoutes(build.dir), {
    "*": 1_000_000,
    "/renamed-away": 1000,
  });

  assertFailureMentions(failures, "/renamed-away");
});

test("budgets without a wildcard default are rejected", () => {
  assert.throws(() => evaluateBudgets([], { "/a": 1 }), /"\*"/);
});
