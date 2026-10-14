"use client";

import { useTranslations } from "next-intl";

export default function CompetitionError({ reset }: { reset: () => void }) {
  const t = useTranslations("competitions.error");
  const tc = useTranslations("common");
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">{tc("errors.somethingWentWrong")}</h1>
          <p className="text-muted-foreground mb-6">
            {t("loadFailed")}
          </p>
          <button
            onClick={reset}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            {tc("actions.retry")}
          </button>
        </div>
      </section>
    </main>
  );
}
