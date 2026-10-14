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
import { ArticleGallery } from "../ArticleGallery";
import { galleryImagesFromElement } from "../gallery-hast";
import { readingMinutes } from "../read-time";
import { remarkGallery } from "../remark-gallery";
import { articleSanitizeSchema } from "../sanitize-schema";
import "../article-markdown.css";
import { ArticleOnward } from "./ArticleOnward";
import type { Onward } from "./onward";
import type { Origin } from "./origin";
import { CroppedImage } from "@/components/CroppedImage";
import { useAuth } from "@/contexts/auth";
import { useNotifications } from "@/contexts/notifications";
import type { Article, Project } from "@/lib/api";
import { formatDate, getAuthorName, pickVariant } from "@/lib/utils";

interface Props {
  project: Project;
  article: Article;
  /** Where the back control goes, resolved on the server from `?from=`. */
  origin: Origin;
  /** What the reader is handed at the end. Null when there is nothing to offer. */
  onward: Onward | null;
  articleCount: number;
  channelCount: number;
}

// A title past this many characters is five lines of display type before the
// reader has read a word, so it steps down a size.
const LONG_TITLE = 70;

export function ArticleRenderContent({
  project,
  article,
  origin,
  onward,
  articleCount,
  channelCount,
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

  const projectSlug = project.slug ?? project.id;
  const iconImage = project.images?.find((img) => img.is_icon);
  const iconUrl = iconImage
    ? pickVariant(iconImage.variants, "thumb") ?? iconImage.url
    : null;

  const standfirst = article.summary || article.summary_display;
  const isLongTitle = article.title.length > LONG_TITLE;

  useEffect(() => {
    if (!isAuthenticated) return;
    markArticleRead(article.id).catch(() => {
      // Best-effort; the bell will eventually reconcile from the server.
    });
  }, [article.id, isAuthenticated, markArticleRead]);

  return (
    <>
      {/*
        No panel and no muted field: the article is the page. The masthead and
        the image band run to the full 6xl the nav and the listing tabs use,
        while the body keeps a 40rem measure — which is what stops the page
        reading as an island without making the prose unreadably wide.
      */}
      <header className="px-4 sm:px-6 pt-4 sm:pt-10">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6 sm:mb-10">
            <Link
              href={origin.href}
              className="inline-flex items-center gap-1.5 pl-2 pr-3 py-1.5 text-sm font-medium rounded-full border border-border bg-white hover:border-accent hover:text-accent transition-colors"
            >
              <ChevronLeftIcon className="w-4 h-4" />
              {origin.label}
            </Link>
          </div>

          {/*
            Centred above sm, left-aligned below it: a centred headline
            wrapping over six lines on a phone reads as a poster rather than
            as something to start reading.
          */}
          <div className="sm:text-center">
            {isDraft && (
              <div className="mb-4 inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
                {t("draftBadge")}
              </div>
            )}

            <Link
              href={`/projects/${projectSlug}`}
              className="inline-flex items-center gap-2 text-sm font-medium hover:text-accent transition-colors"
            >
              {iconUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={iconUrl}
                  alt=""
                  className="w-6 h-6 rounded object-cover border border-border"
                />
              )}
              {project.title}
              <span className="text-muted-foreground font-normal">
                · {article.channel.name}
              </span>
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
                {readingMinutes(article.body)} min read
              </span>
            </div>

            {/*
              With no image there is nothing to mark where the cover ends, so
              the rule does it — the same device an imageless lead card uses in
              ArticleCard, rather than a new one invented here.
            */}
            {!article.listing_image_url && (
              <div className="mt-8 sm:mt-10 h-[3px] w-12 rounded-full bg-accent sm:mx-auto" />
            )}
          </div>
        </div>
      </header>

      {article.listing_image_url && (
        <figure className="max-w-6xl mx-auto px-4 sm:px-6 mt-6 sm:mt-10">
          {/*
            Width-capped, not height-capped. A listing image is framed by the
            crop the author chose, so its aspect is theirs and the height
            follows from the width — bounding the height instead would mean
            clipping their framing. At the full 6xl a 16:9 crop is over 600px
            tall, enough that the body starts below the first screenful on a
            laptop; at 52rem it is under 470px and nothing is cut.
          */}
          <div className="max-w-[52rem] mx-auto rounded-lg sm:rounded-xl overflow-hidden">
            <CroppedImage
              src={article.listing_image_url}
              alt=""
              crop={article.listing_crop}
              priority
              testId="article-listing-image"
            />
          </div>
        </figure>
      )}

      <main className="max-w-[40rem] mx-auto px-4 sm:px-6 pt-8 sm:pt-12 pb-12 sm:pb-16">
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
      </main>

      {onward && (
        <ArticleOnward
          onward={onward}
          project={project}
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
