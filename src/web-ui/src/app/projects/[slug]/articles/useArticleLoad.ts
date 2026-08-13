"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Article, Channel } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";

interface Options {
  projectRef: string;
  articleId: string;
  // The loaded article, for whoever owns the form state.
  onLoaded: (article: Article) => void;
  // Already author-facing: this unit knows what it was doing when it failed, so
  // it picks the fallback sentence. The composite only decides where it shows.
  onError: (message: string) => void;
}

// The initial load: the article being edited plus the project's channels.
// Every callback it takes must be stable — they all land in the load effect's
// deps.
//
// The article always exists by the time this runs: it is created by the New
// article button, because an image cannot be uploaded against an article that
// has no id yet. Nothing here creates one.
export function useArticleLoad({
  projectRef,
  articleId,
  onLoaded,
  onError,
}: Options) {
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
          api.channels.list(projectRef),
          api.articles.get(projectRef, articleId),
        ]);
        if (cancelled) return;

        setChannels(channelList);
        setArticle(loaded);
        onLoaded(loaded);
        setIsLoading(false);
      } catch (err) {
        if (cancelled) return;
        onError(describeApiError(err, "Couldn't open this article."));
        setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [articleId, projectRef, onLoaded, onError]);

  return { channels, article, setArticle, isLoading };
}
