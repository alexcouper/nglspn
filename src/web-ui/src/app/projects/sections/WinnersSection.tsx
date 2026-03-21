"use client";

import Link from "next/link";

import type { WinnerProject } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { HorizontalScroll } from "../HorizontalScroll";

interface WinnersSectionProps {
  winners: WinnerProject[];
}

export function WinnersSection({ winners }: WinnersSectionProps) {
  if (winners.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-semibold text-foreground mb-4">
        Competition Winners
      </h2>
      <HorizontalScroll>
        {winners.map((winner) => (
          <WinnerCard key={`${winner.id}-${winner.competition_slug}`} winner={winner} />
        ))}
      </HorizontalScroll>
    </section>
  );
}

function WinnerCard({ winner }: { winner: WinnerProject }) {
  const imageUrl = winner.hero_banner_url || winner.in_use_image_url;

  return (
    <Link
      href={`/projects/${winner.id}`}
      className="flex flex-shrink-0 w-[280px]"
    >
      <div className="card card-interactive overflow-hidden border-amber-200 hover:shadow-[0_0_20px_rgba(251,191,36,0.15)] flex flex-col w-full">
        <div className="relative aspect-video">
          {imageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imageUrl}
              alt={winner.title}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <GradientPlaceholder id={winner.id} className="w-full h-full" />
          )}
          {/* Winner badge */}
          <span className="absolute top-2 right-2 bg-amber-400 text-amber-900 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full">
            Winner
          </span>
        </div>
        <div className="p-3.5 flex-1 flex flex-col">
          <h3 className="text-sm font-medium text-foreground truncate">
            {winner.title}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1 flex-1">
            {winner.tagline}
          </p>
          <p className="text-xs text-amber-600 font-medium mt-1.5">
            {winner.competition_name}
          </p>
        </div>
      </div>
    </Link>
  );
}
