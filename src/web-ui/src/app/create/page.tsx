"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";
import type { ImportedProject } from "@/lib/project-import";
import { AiImportPanel } from "./AiImportPanel";

type Mode = "link" | "ai";

/**
 * Creating a project, and nothing else. Entering a competition is a separate
 * act on a published project — this page deliberately knows nothing about
 * rounds, and takes no competition parameter.
 */
export default function CreateProjectPage() {
  const router = useRouter();
  const t = useTranslations("my-projects.create");
  const tc = useTranslations("common");
  const { isReady, isLoading: authLoading } = useRequireAuth();
  const [url, setUrl] = useState("");
  const [iOwnThis, setIOwnThis] = useState(true);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("link");

  const createAndOpen = async (fields: ImportedProject) => {
    setIsLoading(true);
    try {
      const project = await api.myProjects.create({
        ...fields,
        is_community_tipoff: !iOwnThis,
      });
      router.push(`/my-projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.submitFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleAiSubmit = (fields: ImportedProject) => {
    setError("");
    void createAndOpen(fields);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      new URL(url);
    } catch {
      setError(t("errors.invalidUrl"));
      return;
    }

    await createAndOpen({ website_url: url, tag_ids: [] });
  };

  const ownership = (
    <fieldset className="space-y-2">
      <legend className="label mb-1">{t("ownershipLegend")}</legend>
      <label htmlFor="ownership-mine" className="flex items-start gap-2 cursor-pointer">
        <input
          id="ownership-mine"
          type="radio"
          name="ownership"
          checked={iOwnThis}
          onChange={() => setIOwnThis(true)}
          className="mt-1"
        />
        <span className="text-sm">
          <span className="text-foreground font-medium">{t("mine")}</span>
          <span className="block text-xs text-muted-foreground">{t("mineDescription")}</span>
        </span>
      </label>
      <label htmlFor="ownership-tipoff" className="flex items-start gap-2 cursor-pointer">
        <input
          id="ownership-tipoff"
          type="radio"
          name="ownership"
          checked={!iOwnThis}
          onChange={() => setIOwnThis(false)}
          className="mt-1"
        />
        <span className="text-sm">
          <span className="text-foreground font-medium">{t("tipoff")}</span>
          <span className="block text-xs text-muted-foreground">{t("tipoffDescription")}</span>
        </span>
      </label>
    </fieldset>
  );

  if (authLoading || !isReady) {
    return (
      <main className="min-h-screen bg-muted flex items-center justify-center pt-14">
        <div className="text-muted-foreground text-sm">{tc("loading")}</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            {t("title")}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t("subtitle")}
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <div className="bg-white border border-border rounded-xl p-6">
            <h2 className="text-foreground font-semibold mb-4">
              {t("formTitle")}
            </h2>
            <div role="tablist" aria-label={t("modeLabel")} className="grid grid-cols-2 gap-1 p-1 mb-5 bg-muted rounded-lg">
              {(["link", "ai"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={`py-1.5 rounded-md text-sm font-medium transition-colors ${
                    mode === m ? "bg-white text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {m === "link" ? t("modeLink") : t("modeAi")}
                </button>
              ))}
            </div>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm mb-4">
                {error}
              </div>
            )}
            {mode === "ai" ? (
              <AiImportPanel isSubmitting={isLoading} onSubmit={handleAiSubmit}>
                {ownership}
              </AiImportPanel>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">

                <div>
                  <label htmlFor="url" className="label">{t("urlLabel")}</label>
                  <input
                    id="url"
                    type="url"
                    required
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="input"
                    placeholder={t("urlPlaceholder")}
                  />
                </div>

                {ownership}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full btn-primary py-2.5"
                >
                  {isLoading ? t("submitting") : t("submit")}
                </button>
              </form>
            )}

            <p className="mt-6 text-center text-sm text-muted-foreground">
              <Link href="/" className="text-accent hover:text-accent-hover font-medium transition-colors">
                {t("backToHome")}
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
