import Link from "next/link";

import { ArticleListingImage } from "@/components/ArticleListingImage";
import { FollowButton } from "@/components/FollowButton";
import type { Project } from "@/lib/api";

import type { Onward, OnwardCard } from "./onward";

interface Props {
  onward: Onward;
  project: Project;
  iconUrl: string | null;
  articleCount: number;
  channelCount: number;
}

// The hand-off at the end of an article. Dark and full-bleed: it is the one
// loud thing on the page, and it is loud because it is where the reader
// decides what to do next instead of reaching for the back button.
//
// One lead card with a row beside it, which is the same lead/row split the
// feed draws on /latest. Three equal cards would leave the narrow two hanging:
// a 16:9 image in a narrow column is shorter than the same ratio in a wide one.
export function ArticleOnward({
  onward,
  project,
  iconUrl,
  articleCount,
  channelCount,
}: Props) {
  const projectSlug = project.slug ?? project.id;

  return (
    <section className="bg-nav-bg text-nav-text px-4 sm:px-6 py-8 sm:py-12">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-baseline justify-between gap-4 pb-5 border-b border-slate-700">
          <h2 className="text-lg font-semibold">{onward.heading}</h2>
          <Link
            href={onward.moreHref}
            className="text-sm text-indigo-300 hover:text-indigo-100 transition-colors shrink-0"
          >
            {onward.moreLabel}
          </Link>
        </div>

        <div className="mt-6 grid gap-6 md:gap-10 md:grid-cols-[1.3fr_1fr] md:items-start">
          <LeadCard card={onward.lead} />

          <div className="grid gap-5 content-start">
            {onward.rest.map((card) => (
              <RowCard key={card.id} card={card} />
            ))}

            {/* The project sits in this column rather than across the foot so
                the column stands level with the lead instead of stopping a
                third of the way down. */}
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
                    {countLine(articleCount, channelCount)}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 mt-3.5">
                <Link
                  href={`/projects/${projectSlug}`}
                  className="text-sm font-medium px-3 py-1.5 rounded-md border border-slate-600 text-slate-200 hover:bg-slate-800 hover:border-slate-500 transition-colors"
                >
                  Project page
                </Link>
                {/* Renders nothing for a signed-out reader, which is most of
                    them — the project link carries the block on its own. */}
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

// Reads as a fact about the project, not a stat block. Channels are only worth
// mentioning once there is more than one.
function countLine(articles: number, channels: number): string {
  const plural = articles === 1 ? "article" : "articles";
  if (channels > 1) return `${articles} ${plural} in ${channels} channels`;
  return `${articles} ${plural}`;
}
