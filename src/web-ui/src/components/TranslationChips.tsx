"use client";

import { useEffect, useRef } from "react";

const PLACEHOLDER_RE = /\{[^{}]+\}/g;

export type ChipsValidation =
  | { ok: true; placeholders: string[] }
  | { ok: false; placeholders: string[]; missing: string[] };

export function extractPlaceholders(text: string): string[] {
  return text.match(PLACEHOLDER_RE) ?? [];
}

export function validateAgainstReference(
  reference: string,
  draft: string,
): ChipsValidation {
  const refPlaceholders = extractPlaceholders(reference).sort();
  const draftPlaceholders = extractPlaceholders(draft).sort();
  const missing = refPlaceholders.filter((p) => !draftPlaceholders.includes(p));
  if (missing.length === 0) {
    return { ok: true, placeholders: refPlaceholders };
  }
  return { ok: false, placeholders: refPlaceholders, missing };
}

export function ChipsEditor({
  value,
  onChange,
  rows = 3,
}: {
  value: string;
  onChange: (next: string) => void;
  rows?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const lastValueRef = useRef<string>("");

  useEffect(() => {
    if (!ref.current) return;
    if (value !== lastValueRef.current) {
      ref.current.innerHTML = renderChipsHtml(value);
      lastValueRef.current = value;
    }
  }, [value]);

  function handleInput() {
    if (!ref.current) return;
    const next = serialize(ref.current);
    lastValueRef.current = next;
    if (next !== value) onChange(next);
  }

  return (
    <div
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      onInput={handleInput}
      role="textbox"
      aria-multiline="true"
      style={{ minHeight: `${rows * 1.5}em` }}
      className="w-full px-2 py-1.5 text-sm border border-border rounded focus:outline-none focus:ring-2 focus:ring-accent whitespace-pre-wrap"
    />
  );
}

function renderChipsHtml(value: string): string {
  const parts: string[] = [];
  let i = 0;
  for (const match of value.matchAll(PLACEHOLDER_RE)) {
    const start = match.index ?? 0;
    if (start > i) parts.push(escapeHtml(value.slice(i, start)));
    parts.push(
      `<span data-chip="${escapeAttr(match[0])}" contenteditable="false" class="inline-block bg-amber-100 text-amber-900 rounded px-1 mx-0.5 text-xs select-none">${escapeHtml(match[0])}</span>`,
    );
    i = start + match[0].length;
  }
  if (i < value.length) parts.push(escapeHtml(value.slice(i)));
  return parts.join("");
}

function serialize(el: HTMLElement): string {
  let out = "";
  for (const node of Array.from(el.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE) {
      out += node.textContent ?? "";
    } else if (node instanceof HTMLElement) {
      const chip = node.dataset.chip;
      if (chip) {
        out += chip;
      } else {
        out += node.textContent ?? "";
      }
    }
  }
  return out;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(s: string): string {
  return escapeHtml(s).replace(/"/g, "&quot;");
}
