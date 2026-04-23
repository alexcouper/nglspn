"use client";

import { useTranslations } from "next-intl";
import { Translatable } from "@/components/Translatable";

export default function ProjectError({ reset }: { reset: () => void }) {
  const t = useTranslations();
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4"><Translatable tKey="error.heading">{t("error.heading")}</Translatable></h1>
          <p className="text-muted-foreground mb-6">
            <Translatable tKey="projects.error.loadProjectMessage">{t("projects.error.loadProjectMessage")}</Translatable>
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Translatable tKey="common.tryAgain">{t("common.tryAgain")}</Translatable>
          </button>
        </div>
      </section>
    </main>
  );
}
