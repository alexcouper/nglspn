import Link from "next/link";
import { useTranslations } from "next-intl";

import { ArticleListingImage } from "@/components/ArticleListingImage";
import { FollowButton } from "@/components/FollowButton";
import type { Project } from "@/lib/api";

import type { Onward, OnwardCard, OnwardHeading } from "./onward";

interface Props {
  onward: Onward;
  project: Project;
  iconUrl: string | null;
  articleCount: number;
  channelCount: number;
}

export function ArticleOnward({
  onward,
  project,
  iconUrl,
  articleCount,
  channelCount,
}: Props) {
  const t = useTranslations("articles.onward");
  const projectSlug = project.slug ?? project.id;
  const [lead, ...rest] = onward.primary.cards;

  const heading = (h: OnwardHeading) => {
    switch (h.kind) {
      case "channel":
        return t("heading.channel", { channel: h.channel });
      case "project":
        return t("heading.project", { project: h.project });
      case "elsewhere":
        return t("heading.elsewhere");
    }
  };

  return (
    <section className="bg-nav-bg text-nav-text px-4 sm:px-6 py-8 sm:py-12">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-baseline justify-between gap-4 pb-5 border-b border-slate-700">
          <h2 className="text-lg font-semibold">
            {heading(onward.primary.heading)}
          </h2>
          <Link
            href={onward.more.href}
            className="text-sm text-indigo-300 hover:text-indigo-100 transition-colors shrink-0"
          >
            {onward.more.kind === "project"
              ? t("moreFromProject", {
                  count: onward.more.count,
                  project: onward.more.project,
                })
              : t("moreLatest")}
          </Link>
        </div>

        <div className="mt-6 grid gap-6 md:gap-10 md:grid-cols-[1.3fr_1fr] md:items-start">
          <LeadCard card={lead} />

          <div className="grid gap-5 content-start">
            {rest.map((card) => (
              <RowCard key={card.id} card={card} />
            ))}

            {onward.topUp && (
              <>
                <h2 className="text-sm font-semibold text-slate-300 pt-5 border-t border-slate-700 first:pt-0 first:border-t-0">
                  {heading(onward.topUp.heading)}
                </h2>
                {onward.topUp.cards.map((card) => (
                  <RowCard key={card.id} card={card} />
                ))}
              </>
            )}

            <div className="pt-5 border-t border-slate-700">
              <div className="flex items-center gap-3">
                {iconUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={iconUrl}
                    alt=""
                    className="w-12 h-12 rounded-lg object-cover shrink-0"
                  />
                )}
                <div className="min-w-0">
                  <div className="font-semibold text-white truncate">
                    {project.title}
                  </div>
                  <div className="text-sm text-slate-400">
                    {channelCount > 1
                      ? t("articleCountInChannels", {
                          count: articleCount,
                          channels: channelCount,
                        })
                      : t("articleCount", { count: articleCount })}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 mt-3.5">
                <Link
                  href={`/projects/${projectSlug}`}
                  className="text-sm font-medium px-3 py-1.5 rounded-md border border-slate-600 text-slate-200 hover:bg-slate-800 hover:border-slate-500 transition-colors"
                >
                  {t("projectPage")}
                </Link>
                {project.slug && <FollowButton projectSlug={project.slug} />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function LeadCard({ card }: { card: OnwardCard }) {
  return (
    <Link href={card.href} className="group block">
      {card.imageUrl && (
        <div className="rounded-lg overflow-hidden">
          <ArticleListingImage src={card.imageUrl} alt="" crop={card.crop} />
        </div>
      )}
      <div className={card.imageUrl ? "mt-3.5" : ""}>
        <Flag>{card.flag}</Flag>
        <h3 className="mt-1.5 text-2xl font-semibold tracking-tight text-white group-hover:text-indigo-200 transition-colors">
          {card.title}
        </h3>
        {card.summary && (
          <p className="mt-2 text-sm text-slate-400 line-clamp-3">{card.summary}</p>
        )}
      </div>
    </Link>
  );
}

function RowCard({ card }: { card: OnwardCard }) {
  return (
    <Link href={card.href} className="group flex gap-3.5 items-start">
      {card.imageUrl && (
        <div className="w-28 shrink-0 rounded-lg overflow-hidden">
          <ArticleListingImage src={card.imageUrl} alt="" crop={card.crop} />
        </div>
      )}
      <div className="min-w-0">
        <Flag>{card.flag}</Flag>
        <h3 className="mt-1 font-semibold text-white line-clamp-2 group-hover:text-indigo-200 transition-colors">
          {card.title}
        </h3>
        {card.summary && (
          <p className="mt-1 text-sm text-slate-400 line-clamp-2">{card.summary}</p>
        )}
      </div>
    </Link>
  );
}

function Flag({ children }: { children: string }) {
  return (
    <div className="text-xs font-semibold uppercase tracking-wide text-indigo-300">
      {children}
    </div>
  );
}
