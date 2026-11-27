"use client";

import { useTranslations } from "next-intl";

import type { FrontPageArticle } from "@/lib/api";
import { DiscoverArticleCard } from "./DiscoverArticleCard";

interface Props {
  articles: FrontPageArticle[];
}

export function SpotlightSection({ articles }: Props) {
  const t = useTranslations("projects.spotlight");
  if (articles.length === 0) return null;

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-foreground">
        {t("heading")}
      </h2>
      <div
        data-testid="spotlight-cards"
        className="grid grid-cols-1 gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3"
      >
        {articles.map((article) => (
          <DiscoverArticleCard key={article.id} article={article} variant="grid" />
        ))}
      </div>
    </section>
  );
}
