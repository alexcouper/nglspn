"use client";

import { useTranslations } from "next-intl";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Translatable } from "@/components/Translatable";
import { BreadcrumbProvider } from "./BreadcrumbContext";
import { Breadcrumbs } from "./Breadcrumbs";

export default function MyReviewsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations();
  const { isReady, isLoading: authLoading } = useRequireAuth();

  if (!authLoading && !isReady) {
    return null;
  }

  return (
    <BreadcrumbProvider>
      <main className="min-h-screen bg-muted pt-14">
        <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
              <Translatable tKey="myReviews.heading">{t("myReviews.heading")}</Translatable>
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              <Translatable tKey="myReviews.subheading">{t("myReviews.subheading")}</Translatable>
            </p>
          </div>
        </section>
        <section className="py-8 px-4 sm:px-6">
          <div className="max-w-4xl mx-auto">
            {authLoading ? (
              <div className="bg-white rounded-xl border border-border p-8">
                <div className="skeleton h-5 w-1/3 mb-3" />
                <div className="skeleton h-4 w-2/3" />
              </div>
            ) : (
              <>
                <Breadcrumbs />
                {children}
              </>
            )}
          </div>
        </section>
      </main>
    </BreadcrumbProvider>
  );
}
