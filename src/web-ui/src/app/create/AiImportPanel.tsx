"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import {
  buildProjectImportPrompt,
  parseProjectImport,
  type ImportError,
  type ImportTagGroup,
  type ImportWarning,
  type ImportedProject,
} from "@/lib/project-import";

interface AiImportPanelProps {
  isSubmitting: boolean;
  onSubmit: (project: ImportedProject) => void;
  /** The ownership fieldset, shared with the plain URL form. */
  children: React.ReactNode;
}

const DESCRIPTION_PREVIEW_CHARS = 280;

/**
 * Bring-your-own-assistant: the site writes the prompt, any AI writes the
 * listing, the site reads it back. Nothing is sent anywhere until the maker
 * presses create — and then only to our own create endpoint.
 */
export function AiImportPanel({ isSubmitting, onSubmit, children }: AiImportPanelProps) {
  const t = useTranslations("my-projects.create.ai");
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
            tags: g.tags.map((tag) => ({ id: tag.id, name: tag.name, slug: tag.slug })),
          })),
        );
      })
      // Without the list the prompt says "no tags" and the import still works.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const prompt = useMemo(() => buildProjectImportPrompt(tagGroups), [tagGroups]);
  const result = useMemo(
    () => (text.trim() ? parseProjectImport(text, tagGroups) : null),
    [text, tagGroups],
  );

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
      case "missingField":
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
    if (result?.ok) onSubmit(result.project);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
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
        <section aria-label={t("previewLabel")} className="border border-border rounded-lg p-4 space-y-2 bg-muted/40">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("previewHeading")}
          </p>
          <p className="text-foreground font-semibold">{result.project.title ?? t("noTitle")}</p>
          {result.project.tagline && (
            <p className="text-sm text-foreground">{result.project.tagline}</p>
          )}
          <p className="text-xs text-muted-foreground break-all">{result.project.website_url}</p>
          {result.project.description ? (
            <p className="text-xs text-muted-foreground whitespace-pre-line">
              {result.project.description.length > DESCRIPTION_PREVIEW_CHARS
                ? `${result.project.description.slice(0, DESCRIPTION_PREVIEW_CHARS)}…`
                : result.project.description}
            </p>
          ) : (
            <p className="text-xs text-amber-700">{t("noDescription")}</p>
          )}
          {result.matchedTags.length > 0 && (
            <ul className="flex flex-wrap gap-1.5" aria-label={t("tagsLabel")}>
              {result.matchedTags.map((tag) => (
                <li key={tag.id} className="badge badge-neutral">
                  {tag.name}
                </li>
              ))}
            </ul>
          )}
          {result.warnings.length > 0 && (
            <ul className="text-xs text-amber-700 list-disc pl-5 space-y-0.5">
              {result.warnings.map((warning, i) => (
                <li key={i}>{describeWarning(warning)}</li>
              ))}
            </ul>
          )}
          <p className="text-xs text-muted-foreground">{t("imagesNote")}</p>
        </section>
      )}

      {children}

      <button type="submit" disabled={!result?.ok || isSubmitting} className="w-full btn-primary py-2.5">
        {isSubmitting ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
