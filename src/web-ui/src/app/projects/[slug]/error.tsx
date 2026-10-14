"use client";

import { useTranslations } from "next-intl";

export default function ProjectError({ reset }: { reset: () => void }) {
  const t = useTranslations("projects.projectError");
  const te = useTranslations("common.errors");
  const ta = useTranslations("common.actions");
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">{te("somethingWentWrong")}</h1>
          <p className="text-muted-foreground mb-6">
            {t("description")}
          </p>
          <button
            onClick={reset}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            {ta("retry")}
          </button>
        </div>
      </section>
    </main>
  );
}
