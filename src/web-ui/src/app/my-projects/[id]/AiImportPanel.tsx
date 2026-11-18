"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import {
  buildProjectImportPrompt,
  parseProjectImport,
  type ImportError,
  type ImportTag,
  type ImportTagGroup,
  type ImportWarning,
  type ImportedProject,
} from "@/lib/project-import";
import type { ProjectFormData } from "./ProjectDetail";

interface AiImportPanelProps {
  /** The form as it stands, unsaved edits included: what the prompt shows and the preview compares against. */
  current: ProjectFormData;
  onApply: (fields: ImportedProject, matchedTags: ImportTag[]) => void;
}

const DESCRIPTION_PREVIEW_CHARS = 280;

type ChangedField = "title" | "tagline" | "website_url" | "description" | "tags";

function sameIds(a: string[], b: string[]) {
  return a.length === b.length && [...a].sort().join() === [...b].sort().join();
}

/**
 * Bring-your-own-assistant: the site writes the prompt (with the listing as it
 * is now), any AI rewrites it, the site reads it back into the form. Nothing is
 * sent anywhere; the maker still presses Save.
 */
export function AiImportPanel({ current, onApply }: AiImportPanelProps) {
  const t = useTranslations("my-projects.editContent.ai");
  const [tagGroups, setTagGroups] = useState<ImportTagGroup[]>([]);
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [fileError, setFileError] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.tags
      .listGrouped()
      .then((groups) => {
        if (cancelled) return;
        setTagGroups(
          groups.map((g) => ({
            category: g.category.name,
            tags: g.tags.map((tag) => ({ id: tag.id, name: tag.name, slug: tag.slug, color: tag.color })),
          })),
        );
      })
      // Without the list the prompt says "no tags" and the rest still works.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const tagName = useMemo(() => {
    const names = new Map(tagGroups.flatMap((g) => g.tags).map((tag) => [tag.id, tag.name]));
    return (id: string) => names.get(id);
  }, [tagGroups]);

  const prompt = useMemo(
    () =>
      buildProjectImportPrompt(tagGroups, {
        website_url: current.website_url,
        title: current.title,
        tagline: current.tagline,
        description: current.description,
        tags: current.tag_ids.map(tagName).filter((n): n is string => !!n),
      }),
    [tagGroups, current, tagName],
  );
  const result = useMemo(
    () => (text.trim() ? parseProjectImport(text, tagGroups) : null),
    [text, tagGroups],
  );

  const changed: ChangedField[] = useMemo(() => {
    if (!result?.ok) return [];
    const p = result.project;
    const fields: ChangedField[] = [];
    for (const field of ["title", "tagline", "website_url", "description"] as const) {
      if (p[field] !== undefined && p[field] !== current[field]) fields.push(field);
    }
    if (p.tag_ids && !sameIds(p.tag_ids, current.tag_ids)) fields.push("tags");
    return fields;
  }, [result, current]);

  const copyPrompt = async () => {
    setCopyFailed(false);
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyFailed(true);
    }
  };

  const downloadPrompt = () => {
    const blob = new Blob([prompt], { type: "text/markdown" });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = "naglasupan-project-prompt.md";
    link.click();
    // Revoking synchronously can cancel the download in some browsers.
    setTimeout(() => URL.revokeObjectURL(href), 0);
  };

  const readFile = async (files: FileList | null) => {
    setFileError(false);
    const file = files?.[0];
    if (!file) return;
    try {
      setText(await file.text());
    } catch {
      setFileError(true);
    }
    if (fileInput.current) fileInput.current.value = "";
  };

  const describeError = (error: ImportError) => {
    switch (error.code) {
      case "noJson":
      case "invalidJson":
        return t(`errors.${error.code}`);
      case "unsupportedFormat":
        return t("errors.unsupportedFormat", { value: error.value });
      case "wrongType":
      case "invalidUrl":
        return t(`errors.${error.code}`, { field: error.field });
      case "tooLong":
        return t("errors.tooLong", { field: error.field, max: error.max, length: error.length });
    }
  };

  const describeWarning = (warning: ImportWarning) => t(`warnings.${warning.code}`, { value: warning.value });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!result?.ok || changed.length === 0) return;
    onApply(result.project, result.matchedTags);
    setText("");
  };

  const renderValue = (field: ChangedField) => {
    if (!result?.ok) return null;
    const p = result.project;
    switch (field) {
      case "title":
        return <p className="text-foreground font-semibold">{p.title}</p>;
      case "tagline":
        return <p className="text-sm text-foreground">{p.tagline}</p>;
      case "website_url":
        return <p className="text-xs text-muted-foreground break-all">{p.website_url}</p>;
      case "description": {
        const d = p.description ?? "";
        return (
          <p className="text-xs text-muted-foreground whitespace-pre-line">
            {d.length > DESCRIPTION_PREVIEW_CHARS ? `${d.slice(0, DESCRIPTION_PREVIEW_CHARS)}…` : d}
          </p>
        );
      }
      case "tags":
        return (
          <ul className="flex flex-wrap gap-1.5">
            {result.matchedTags.map((tag) => (
              <li key={tag.id} className="badge badge-neutral">
                {tag.name}
              </li>
            ))}
          </ul>
        );
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="ai-tab">
      <ol className="space-y-6">
        <li>
          <h3 className="text-sm font-semibold text-foreground">{t("step1Title")}</h3>
          <p className="text-xs text-muted-foreground mt-1">{t("step1Body")}</p>
          <div className="flex flex-wrap gap-2 mt-3">
            <button type="button" onClick={copyPrompt} className="btn-secondary py-2 px-4">
              {copied ? t("copied") : t("copyPrompt")}
            </button>
            <button type="button" onClick={downloadPrompt} className="btn-secondary py-2 px-4">
              {t("downloadPrompt")}
            </button>
          </div>
          {copyFailed && (
            <div className="mt-3">
              <p className="text-xs text-red-700 mb-1">{t("copyFailed")}</p>
              <textarea
                readOnly
                value={prompt}
                rows={6}
                aria-label={t("promptLabel")}
                className="input font-mono text-xs"
                onFocus={(e) => e.currentTarget.select()}
              />
            </div>
          )}
        </li>

        <li>
          <h3 className="text-sm font-semibold text-foreground">{t("step2Title")}</h3>
          <p className="text-xs text-muted-foreground mt-1">{t("step2Body")}</p>
        </li>

        <li>
          <label htmlFor="ai-output" className="text-sm font-semibold text-foreground block">
            {t("step3Title")}
          </label>
          <textarea
            id="ai-output"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            className="input font-mono text-xs mt-2"
            placeholder={t("pastePlaceholder")}
          />
          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
            <span>{t("or")}</span>
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="text-accent hover:text-accent-hover font-medium"
            >
              {t("uploadFile")}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept=".json,application/json,.txt,text/plain,.md,text/markdown"
              className="hidden"
              aria-label={t("uploadFile")}
              onChange={(e) => readFile(e.target.files)}
            />
          </div>
          {fileError && <p className="text-xs text-red-700 mt-1">{t("errors.fileUnreadable")}</p>}
        </li>
      </ol>

      {result && !result.ok && (
        <div role="alert" className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm">
          <p className="font-medium">{t("cannotUse")}</p>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            {result.errors.map((error, i) => (
              <li key={i}>{describeError(error)}</li>
            ))}
          </ul>
        </div>
      )}

      {result?.ok && (
        <section aria-label={t("previewLabel")} className="border border-border rounded-lg p-4 space-y-3 bg-muted/40">
          {changed.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("noChanges")}</p>
          ) : (
            <>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {t("previewHeading")}
              </p>
              <dl className="space-y-3">
                {changed.map((field) => (
                  <div key={field}>
                    <dt className="text-xs font-medium text-muted-foreground">{t(`fields.${field}`)}</dt>
                    <dd className="mt-0.5">{renderValue(field)}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-xs text-muted-foreground">{t("keptNote")}</p>
            </>
          )}
          {result.warnings.length > 0 && (
            <ul className="text-xs text-amber-700 list-disc pl-5 space-y-0.5">
              {result.warnings.map((warning, i) => (
                <li key={i}>{describeWarning(warning)}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div>
        <button type="submit" disabled={!result?.ok || changed.length === 0} className="w-full btn-primary py-2.5">
          {t("submit")}
        </button>
        <p className="text-xs text-muted-foreground mt-2 text-center">{t("notSavedNote")}</p>
      </div>
    </form>
  );
}
