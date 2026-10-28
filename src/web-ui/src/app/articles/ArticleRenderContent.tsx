"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ChevronLeftIcon } from "@heroicons/react/24/outline";
import ReactMarkdown from "react-markdown";
import rehypePrismPlus from "rehype-prism-plus";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import remarkDirective from "remark-directive";
import remarkGfm from "remark-gfm";
import { ArticleGallery } from "./ArticleGallery";
import { galleryImagesFromElement } from "./gallery-hast";
import { readingMinutes } from "./read-time";
import { remarkGallery } from "./remark-gallery";
import { articleSanitizeSchema } from "./sanitize-schema";
import "./article-markdown.css";
import { ArticleOnward } from "./ArticleOnward";
import type { Onward } from "./onward";
import type { Origin } from "./origin";
import { ArticleCover } from "./ArticleCover";
import { Avatar } from "@/components/Avatar";
import { useAuth } from "@/contexts/auth";
import { useNotifications } from "@/contexts/notifications";
import type { Article } from "@/lib/api";
import { formatDate, getAuthorName, pickVariant } from "@/lib/utils";
import { type Container, containerHref, containerTitle } from "./container";

interface Props {
  container: Container;
  article: Article;
  origin: Origin;
  onward: Onward | null;
  articleCount: number;
  channelCount: number;
  // Rendered inside the editor: nothing is marked read, since the author is
  // looking at their own draft.
  preview?: boolean;
}

// Past this a title steps down a size.
const LONG_TITLE = 70;

export function ArticleRenderContent({
  container,
  article,
  origin,
  onward,
  articleCount,
  channelCount,
  preview = false,
}: Props) {
  const t = useTranslations("articles.render");
  const { isAuthenticated } = useAuth();
  // Through the context, not api.notifications directly: it refreshes the
  // summary afterwards, so the bell drops its count now rather than at the
  // next 30s poll.
  const { markArticleRead } = useNotifications();

  const publishedAt = article.published_at
    ? new Date(article.published_at)
    : null;
  const isDraft = article.state !== "published";

  const project = container.kind === "project" ? container.project : null;
  const iconImage = project?.images?.find((img) => img.is_icon);
  const iconUrl = iconImage
    ? pickVariant(iconImage.variants, "thumb") ?? iconImage.url
    : null;

  const standfirst = article.summary || article.summary_display;
  const isLongTitle = article.title.length > LONG_TITLE;
  // The cover is the one image the author picked for the article; the cards
  // show the same one. Nothing is derived from the body.
  const coverUrl = article.listing_image_url;

  useEffect(() => {
    if (!isAuthenticated || preview) return;
    markArticleRead(article.id).catch(() => {
      // Best-effort; the bell will eventually reconcile from the server.
    });
  }, [article.id, isAuthenticated, markArticleRead, preview]);

  return (
    <>
      <article>
        <header className="px-4 sm:px-6 pt-4 sm:pt-10">
          <div className="max-w-6xl mx-auto">
            <div className="mb-6 sm:mb-10">
              <Link
                href={origin.href}
                className="inline-flex items-center gap-1.5 pl-2 pr-3 py-1.5 text-sm font-medium rounded-full border border-border bg-white hover:border-accent hover:text-accent transition-colors"
              >
                <ChevronLeftIcon className="w-4 h-4" />
                {origin.kind === "container" ? origin.title : t("backToLatest")}
              </Link>
            </div>

            <div className="sm:text-center">
              {isDraft && (
                <div className="mb-4 inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
                  {t("draftBadge")}
                </div>
              )}

              {/* Where the article lives: the project's icon and title, or
                  the author's avatar and name. A person's channel is a
                  placeholder, so only a project's is shown. */}
              <Link
                href={containerHref(container)}
                className="inline-flex items-center gap-2 text-sm font-medium hover:text-accent transition-colors"
                data-testid="article-container"
              >
                {project ? (
                  iconUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={iconUrl}
                      alt=""
                      className="w-6 h-6 rounded object-cover border border-border"
                    />
                  )
                ) : (
                  <Avatar
                    src={container.kind === "author" ? container.author.avatar_url : null}
                    firstName={container.kind === "author" ? container.author.first_name : ""}
                    lastName={container.kind === "author" ? container.author.last_name : ""}
                    size={24}
                  />
                )}
                {containerTitle(container)}
                {project && article.channel && (
                  <span className="text-muted-foreground font-normal">
                    · {article.channel.name}
                  </span>
                )}
              </Link>

              <h1
                className={`mt-4 font-semibold tracking-tight text-balance sm:mx-auto ${
                  isLongTitle
                    ? "text-[1.625rem] sm:text-4xl sm:max-w-[40rem]"
                    : "text-3xl sm:text-5xl sm:max-w-[46rem]"
                }`}
              >
                {article.title}
              </h1>

              {standfirst && (
                <p className="mt-4 text-lg text-muted-foreground sm:mx-auto sm:max-w-[34rem] text-pretty">
                  {standfirst}
                </p>
              )}

              <div className="mt-7 inline-flex items-center gap-2.5 text-sm text-muted-foreground">
                {article.author && !article.author.is_system_user && (
                  <span className="w-8 h-8 rounded-full bg-accent-subtle text-accent-hover grid place-items-center text-xs font-semibold shrink-0">
                    {initials(getAuthorName(article.author))}
                  </span>
                )}
                <span>
                  {article.author && !article.author.is_system_user && (
                    <>
                      <Link
                        href={`/users/${article.author.id}`}
                        className="text-foreground font-medium hover:text-accent transition-colors"
                      >
                        {getAuthorName(article.author)}
                      </Link>
                      {" · "}
                    </>
                  )}
                  {publishedAt && (
                    <time dateTime={publishedAt.toISOString()}>
                      {formatDate(publishedAt)}
                    </time>
                  )}
                  {publishedAt && " · "}
                  {t("readTime", { minutes: readingMinutes(article.body) })}
                </span>
              </div>

              {!coverUrl && (
                <div className="mt-8 sm:mt-10 h-[3px] w-12 rounded-full bg-accent sm:mx-auto" />
              )}
            </div>
          </div>
        </header>

        {coverUrl && (
          <figure className="max-w-6xl mx-auto px-4 sm:px-6 mt-6 sm:mt-10">
            <ArticleCover src={coverUrl} crop={article.listing_crop} priority />
          </figure>
        )}

        <div className="max-w-[40rem] mx-auto px-4 sm:px-6 pt-8 sm:pt-12 pb-12 sm:pb-16">
          <div className="markdown markdown-article">
            <ReactMarkdown
              // remarkDirective parses `:::gallery`; remarkGallery must follow
              // it, because it is what turns those nodes into something
              // renderable — and what puts every directive it does not
              // recognise back as the literal text the author typed.
              remarkPlugins={[remarkGfm, remarkDirective, remarkGallery]}
              // Plugin order matters: rehypeRaw first to turn HTML strings into
              // hast nodes; rehypePrismPlus second so it can syntax-highlight
              // fenced code blocks into <span class="token …"> tokens;
              // rehypeSanitize last to strip anything outside the allowlist
              // (which now permits className on pre/code/span so Prism's
              // output survives).
              rehypePlugins={[
                rehypeRaw,
                [rehypePrismPlus, { ignoreMissing: true }],
                [rehypeSanitize, articleSanitizeSchema],
              ]}
              components={{
                div: ({ node, children, ...props }) => {
                  const images = galleryImagesFromElement(node);
                  return images ? (
                    <ArticleGallery images={images} />
                  ) : (
                    <div {...props}>{children}</div>
                  );
                },
                table: ({ children }) => (
                  <div className="my-6 overflow-x-auto">
                    <table className="w-full text-sm border border-border rounded-lg overflow-hidden border-collapse">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-muted">{children}</thead>
                ),
                tr: ({ children }) => (
                  <tr className="border-b border-border last:border-b-0">
                    {children}
                  </tr>
                ),
                th: ({ children }) => (
                  <th className="px-3.5 py-2.5 text-left font-semibold text-foreground align-top">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-3.5 py-2.5 text-left align-top">
                    {children}
                  </td>
                ),
              }}
            >
              {article.body}
            </ReactMarkdown>
          </div>
        </div>
      </article>

      {onward && (
        <ArticleOnward
          onward={onward}
          container={container}
          iconUrl={iconUrl}
          articleCount={articleCount}
          channelCount={channelCount}
        />
      )}
    </>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
