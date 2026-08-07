"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Article, Channel } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";

interface Options {
  projectRef: string;
  // Present → editing an existing article. Absent → the /new route, which
  // creates a draft immediately rather than waiting for a save.
  articleId?: string;
  // The loaded or created article, for whoever owns the form state.
  onLoaded: (article: Article) => void;
  // Reported, not acted on: this unit has no router, so the page decides what a
  // newly created article means for the URL.
  onCreated: (article: Article) => void;
  // Already author-facing: this unit knows what it was doing when it failed, so
  // it picks the fallback sentence. The composite only decides where it shows.
  onError: (message: string) => void;
}

// The initial load: the project's channels plus either the article being edited
// or a freshly created draft. Every callback it takes must be stable — they all
// land in the load effect's deps.
export function useArticleLoad({
  projectRef,
  articleId,
  onLoaded,
  onCreated,
  onError,
}: Options) {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // React StrictMode runs effects twice in development. Without this guard
  // opening /new would create two drafts per visit.
  const creatingRef = useRef(false);

  const isEditing = !!articleId;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const channelList = await api.channels.list(projectRef);
        if (cancelled) return;
        setChannels(channelList);

        // An upload cannot name an article that does not exist yet, so /new
        // creates an empty draft up front and the page swaps the URL to
        // /edit/<id> — the same swap that used to happen on first save, moved
        // earlier.
        let loaded: Article;
        if (isEditing) {
          loaded = await api.articles.get(projectRef, articleId!);
        } else {
          if (creatingRef.current) return;
          creatingRef.current = true;
          loaded = await api.articles.create(projectRef, {
            channel_id: channelList[0]?.id ?? "",
            title: "",
            body: "",
          });
          if (cancelled) return;
          onCreated(loaded);
        }
        if (cancelled) return;

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
  }, [isEditing, articleId, projectRef, onCreated, onLoaded, onError]);

  return { channels, article, setArticle, isLoading };
}
