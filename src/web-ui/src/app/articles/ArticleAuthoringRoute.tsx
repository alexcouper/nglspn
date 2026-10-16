"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { Article, Project } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { ArticleAuthoringPage } from "./ArticleAuthoringPage";
import { ArticleAuthoringSkeleton } from "./ArticleAuthoringSkeleton";

interface Props {
  // Always an existing article: the Write article buttons create the draft
  // before routing here, so this wrapper only ever serves the /edit route.
  articleId: string;
}

type Loaded = { article: Article; project: Project | null };

// Loads the article client-side so the request carries the bearer token, then
// its project if it has one. The route page above this is a server component,
// and no server component here can authenticate — the token is in
// localStorage — so a server fetch always looks anonymous to the backend,
// which 404s every article the caller may edit but readers may not see yet.
// The project is only needed for the channel dropdown and the breadcrumb; an
// author-owned article has neither.
export function ArticleAuthoringRoute({ articleId }: Props) {
  const { isReady } = useRequireAuth();
  const t = useTranslations("articles.route");
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [error, setError] = useState("");

  // The editor is by far the largest thing on this route — the bundle budget
  // gives it 400 kB against 55 kB for everything else. next/dynamic only starts
  // its import when the component first renders, and ArticleAuthoringPage does
  // not render until the article below has landed, so the biggest download
  // would otherwise queue behind a round trip it does not depend on. Warmed
  // here it downloads alongside the article. Same specifier as the dynamic()
  // in ArticleAuthoringPage, so this is the same chunk, not a second copy.
  // `isReady` is read from the stored token, not the network, so gating on it
  // costs nothing and spares a visitor on their way to /login the 400 kB.
  useEffect(() => {
    if (!isReady) return;
    void import("./ArticleEditor");
  }, [isReady]);

  useEffect(() => {
    // Not signed in: useRequireAuth is already routing to /login. Requesting
    // the article first would only show a "not found" on the way out.
    if (!isReady) return;

    let cancelled = false;
    api.articles
      .get(articleId)
      .then(async (article) => {
        const project = article.project
          ? await api.projects.get(article.project.slug ?? article.project.id)
          : null;
        if (!cancelled) setLoaded({ article, project });
      })
      .catch((err) => {
        if (!cancelled) {
          setError(describeApiError(err, t("openArticleFailed.fallback")));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [articleId, isReady, t]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-lg font-semibold text-foreground">
          {t("openArticleFailed.title")}
        </h1>
        <p className="text-sm text-muted-foreground mt-2" role="alert">
          {error}
        </p>
        <div className="mt-6">
          <Link
            href="/my-projects"
            className="text-sm text-accent hover:text-accent-hover"
          >
            {t("backToMyProjects")}
          </Link>
        </div>
      </div>
    );
  }

  if (!loaded) {
    return <ArticleAuthoringSkeleton />;
  }

  return (
    <ArticleAuthoringPage
      project={loaded.project}
      initialArticle={loaded.article}
    />
  );
}
