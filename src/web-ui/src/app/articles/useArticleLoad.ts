"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { Article, Channel } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";

interface Options {
  // The project's slug or id, or null for an author-owned article, which has
  // no channels to list.
  projectRef: string | null;
  articleId: string;
  // The article, when the route has already fetched it to find its project.
  // Without it the hook fetches by id.
  initialArticle?: Article | null;
  // The loaded article, for whoever owns the form state.
  onLoaded: (article: Article) => void;
  // Already author-facing: this unit knows what it was doing when it failed, so
  // it picks the fallback sentence. The composite only decides where it shows.
  onError: (message: string) => void;
}

// The initial load: the article being edited plus, on a project, its channels.
// Every callback it takes must be stable — they all land in the load effect's
// deps.
//
// The article always exists by the time this runs: it is created by the Write
// article button, because an image cannot be uploaded against an article that
// has no id yet. Nothing here creates one.
export function useArticleLoad({
  projectRef,
  articleId,
  initialArticle = null,
  onLoaded,
  onError,
}: Options) {
  const t = useTranslations("articles.load");
  // Resolved outside the effect so the effect depends on a string, which is
  // stable by value, rather than on the translator function.
  const openFailed = t("openFailed");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        // Independent reads, so they go together: the article is what the page
        // blocks on, and making it queue behind the channel list only delayed
        // the editor by a round trip.
        const [channelList, loaded] = await Promise.all([
          projectRef ? api.channels.list(projectRef) : Promise.resolve([]),
          initialArticle ?? api.articles.get(articleId),
        ]);
        if (cancelled) return;

        setChannels(channelList);
        setArticle(loaded);
        onLoaded(loaded);
        setIsLoading(false);
      } catch (err) {
        if (cancelled) return;
        onError(describeApiError(err, openFailed));
        setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [articleId, projectRef, initialArticle, onLoaded, onError, openFailed]);

  return { channels, article, setArticle, isLoading };
}
