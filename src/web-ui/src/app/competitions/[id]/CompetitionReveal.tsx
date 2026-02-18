"use client";

import { useState, useEffect, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import { TrophyIcon } from "@heroicons/react/24/solid";
import {
  api,
  type Competition,
  type CompetitionProject,
} from "@/lib/api";
import { getPlaceholderColor } from "@/lib/utils";
import { TagFilterUnified } from "@/components/TagFilterUnified";
import { TagBadge } from "@/components/TagBadge";

function formatDateRange(startDate: string, endDate: string): string {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const options: Intl.DateTimeFormatOptions = {
    month: "long",
    day: "numeric",
    year: "numeric",
  };
  return `${start.toLocaleDateString("en-US", options)} - ${end.toLocaleDateString("en-US", options)}`;
}

interface CompetitionRevealProps {
  competitionId: string;
}

export function CompetitionReveal({ competitionId }: CompetitionRevealProps) {
  const [competition, setCompetition] = useState<Competition | null>(null);
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchCompetition = async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await api.competitions.get(competitionId);
        setCompetition(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch competition"
        );
      }
      setIsLoading(false);
    };

    fetchCompetition();
  }, [competitionId]);

  const { tags, categories } = useMemo(() => {
    if (!competition) return { tags: [], categories: [] };

    const tagMap = new Map<string, {
      id: string;
      name: string;
      slug: string;
      color: string | null;
      category_id: string | null;
      category_slug: string | null;
    }>();
    const categoryMap = new Map<string, { id: string; name: string; slug: string }>();

    for (const project of competition.projects) {
      for (const tag of project.tags) {
        if (!tagMap.has(tag.id)) {
          tagMap.set(tag.id, {
            id: tag.id,
            name: tag.name,
            slug: tag.slug,
            color: tag.color,
            category_id: tag.category_id || null,
            category_slug: tag.category_slug || null,
          });
        }
        const catId = tag.category_id;
        const catSlug = tag.category_slug;
        if (catId && catSlug && !categoryMap.has(catId)) {
          categoryMap.set(catId, {
            id: catId,
            name: catSlug.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" "),
            slug: catSlug,
          });
        }
      }
    }

    return {
      tags: Array.from(tagMap.values()),
      categories: Array.from(categoryMap.values()),
    };
  }, [competition]);

  const filteredProjects = useMemo(() => {
    if (!competition) return [];
    if (selectedTagIds.length === 0) return competition.projects;
    return competition.projects.filter((project) =>
      project.tags.some((tag) => selectedTagIds.includes(tag.id))
    );
  }, [competition, selectedTagIds]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-border p-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="skeleton w-14 h-14 rounded-full" />
          <div>
            <div className="skeleton h-6 w-48 mb-2" />
            <div className="skeleton h-4 w-32" />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="skeleton aspect-video rounded-t-lg" />
              <div className="bg-white border border-t-0 border-border rounded-b-lg p-3">
                <div className="skeleton h-4 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error}
      </div>
    );
  }

  if (!competition) {
    return (
      <p className="text-muted-foreground text-sm text-center py-12">Competition not found.</p>
    );
  }

  const isAcceptingApplications =
    competition.status === "accepting_applications";
  const iconPlaceholderColor = getPlaceholderColor(competition.id);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-border p-6">
        <div className="flex items-center gap-4">
          <div
            className={`relative w-14 h-14 rounded-full overflow-hidden flex-shrink-0 ${!competition.image_url ? iconPlaceholderColor : ""}`}
          >
            {competition.image_url && (
              <Image
                src={competition.image_url}
                alt={competition.name}
                fill
                className="object-cover"
                sizes="56px"
                priority
              />
            )}
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-semibold text-foreground tracking-tight">
              {competition.name}
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {formatDateRange(competition.start_date, competition.end_date)}
            </p>
          </div>
        </div>
        {isAcceptingApplications && (
          <div className="mt-5">
            <Link href="/submit" className="btn-primary">
              Submit a project
            </Link>
          </div>
        )}
      </div>

      {!isAcceptingApplications && (
        <div className="flex gap-8">
          {/* Sidebar filters */}
          {tags.length > 0 && (
            <div className="hidden md:block w-56 flex-shrink-0">
              <TagFilterUnified
                mode="local"
                tags={tags}
                categories={categories}
                selectedIds={selectedTagIds}
                onFilterChange={setSelectedTagIds}
              />
            </div>
          )}

          {/* Main */}
          <div className="flex-1 min-w-0 space-y-6">
            {/* Quote */}
            {competition.quote && (
              <blockquote className="bg-white rounded-xl border border-border p-5 border-l-3 border-l-accent">
                <p className="text-sm text-muted-foreground italic leading-relaxed">
                  &ldquo;{competition.quote}&rdquo;
                </p>
              </blockquote>
            )}

            {/* Winner */}
            {competition.winner && (
              <div className="bg-white rounded-xl border border-amber-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrophyIcon className="w-5 h-5 text-amber-500" />
                  <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">Winner</h2>
                </div>
                <WinnerCard project={competition.winner} />
              </div>
            )}

            {/* Mobile filter */}
            {tags.length > 0 && (
              <div className="md:hidden">
                <TagFilterUnified
                  mode="local"
                  tags={tags}
                  categories={categories}
                  selectedIds={selectedTagIds}
                  onFilterChange={setSelectedTagIds}
                />
              </div>
            )}

            {/* Projects */}
            <div>
              <div className="flex items-baseline gap-2 mb-4">
                <h2 className="text-base font-semibold text-foreground">
                  {selectedTagIds.length > 0 ? "Filtered Projects" : "All Projects"}
                </h2>
                <span className="text-xs text-muted-foreground">
                  ({filteredProjects.length})
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {filteredProjects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    isWinner={project.id === competition.winner?.id}
                  />
                ))}
                {filteredProjects.length === 0 && (
                  <p className="col-span-full text-muted-foreground text-sm text-center py-8">
                    No projects found
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function WinnerCard({ project }: { project: CompetitionProject }) {
  const placeholderColor = getPlaceholderColor(project.id);

  return (
    <Link
      href={`/projects/${project.id}`}
      className="group block card card-interactive"
    >
      <div className="flex flex-col sm:flex-row">
        <div
          className={`relative aspect-video sm:w-56 sm:aspect-auto sm:h-36 ${!project.main_image_url ? placeholderColor : "bg-slate-100"}`}
        >
          {project.main_image_url && (
            <Image
              src={project.main_image_url}
              alt={project.title}
              fill
              className="object-contain"
              sizes="(max-width: 640px) 100vw, 224px"
            />
          )}
        </div>
        <div className="p-4 flex-1">
          <h3 className="font-semibold text-foreground group-hover:text-accent transition-colors">
            {project.title || "Untitled"}
          </h3>
          {project.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {project.tags.map((tag) => (
                <TagBadge key={tag.id} name={tag.name} color={tag.color} size="sm" />
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

function ProjectCard({
  project,
  isWinner,
}: {
  project: CompetitionProject;
  isWinner: boolean;
}) {
  const placeholderColor = getPlaceholderColor(project.id);

  return (
    <Link
      href={`/projects/${project.id}`}
      className={`card card-interactive group ${
        isWinner ? "border-amber-300 ring-1 ring-amber-200" : ""
      }`}
    >
      <div
        className={`relative aspect-video ${!project.main_image_url ? placeholderColor : "bg-slate-100"}`}
      >
        {project.main_image_url && (
          <Image
            src={project.main_image_url}
            alt={project.title}
            fill
            className="object-contain"
            sizes="(max-width: 768px) 50vw, 33vw"
          />
        )}
        {isWinner && (
          <div className="absolute top-2 right-2 bg-amber-500 text-white p-1 rounded-full shadow-sm">
            <TrophyIcon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>
      <div className="p-3.5">
        <h3 className="font-medium text-sm text-foreground truncate group-hover:text-accent transition-colors">
          {project.title || "Untitled"}
        </h3>
        {project.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {project.tags.slice(0, 2).map((tag) => (
              <TagBadge key={tag.id} name={tag.name} color={tag.color} size="sm" />
            ))}
            {project.tags.length > 2 && (
              <span className="text-xs text-muted-foreground">+{project.tags.length - 2}</span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
