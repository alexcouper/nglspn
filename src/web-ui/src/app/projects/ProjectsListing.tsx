"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import {
  Squares2X2Icon,
  TrophyIcon as TrophyIconOutline,
  ArrowsUpDownIcon,
  FunnelIcon,
} from "@heroicons/react/24/outline";
import { TrophyIcon } from "@heroicons/react/24/solid";
import {
  api,
  type Project,
  type Competition,
  type CompetitionProject,
} from "@/lib/api";
import { getPlaceholderColor } from "@/lib/utils";
import { TagFilterUnified } from "@/components/TagFilterUnified";
import { TagBadge } from "@/components/TagBadge";

type SortBy = "created_at" | "title";
type ViewMode = "list" | "competition";

export function ProjectsListing() {
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [pendingProjectsCount, setPendingProjectsCount] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [sortBy, setSortBy] = useState<SortBy>("title");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const sortDropdownRef = useRef<HTMLDivElement>(null);

  const selectedTags = searchParams.get("tags")?.split(",").filter(Boolean) || [];

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError("");
      try {
        if (viewMode === "competition") {
          const data = await api.competitions.listWithProjects();
          setCompetitions(data.competitions);
          setPendingProjectsCount(data.pending_projects_count);
        } else {
          const sortOrder = sortBy === "title" ? "asc" : "desc";
          const tags = searchParams.get("tags")?.split(",").filter(Boolean) || [];
          const data = await api.projects.list({
            sort_by: sortBy,
            sort_order: sortOrder,
            tags: tags.length > 0 ? tags : undefined,
          });
          setProjects(data.projects);
          setPendingProjectsCount(data.pending_projects_count);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      }
      setIsLoading(false);
    };

    fetchData();
  }, [viewMode, sortBy, searchParams]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        sortDropdownRef.current &&
        !sortDropdownRef.current.contains(event.target as Node)
      ) {
        setSortDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="flex gap-8">
      {/* Sidebar filters */}
      <div
        className={`${
          showFilters ? "block" : "hidden"
        } md:block w-full md:w-56 flex-shrink-0`}
      >
        <TagFilterUnified mode="api" withProjects multiSelect useUrlParams />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        {/* Controls */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowFilters(!showFilters)}
              title="Toggle filters"
              className={`md:hidden p-2 rounded-lg transition-colors ${
                showFilters || selectedTags.length > 0
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <FunnelIcon className="w-4.5 h-4.5" />
              {selectedTags.length > 0 && (
                <span className="ml-1 inline-flex items-center justify-center w-4 h-4 text-[10px] bg-accent text-white rounded-full">
                  {selectedTags.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setViewMode("list")}
              title="All projects"
              className={`p-2 rounded-lg transition-colors ${
                viewMode === "list"
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Squares2X2Icon className="w-4.5 h-4.5" />
            </button>
            <button
              onClick={() => setViewMode("competition")}
              title="By competition"
              className={`p-2 rounded-lg transition-colors ${
                viewMode === "competition"
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <TrophyIconOutline className="w-4.5 h-4.5" />
            </button>
          </div>

          <div className="relative" ref={sortDropdownRef}>
            <button
              onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
              title="Sort order"
              className="p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <ArrowsUpDownIcon className="w-4.5 h-4.5" />
            </button>
            {sortDropdownOpen && (
              <div className="absolute right-0 mt-1 bg-white rounded-lg shadow-lg border border-border py-1 z-10 min-w-[140px]">
                <button
                  onClick={() => { setSortBy("created_at"); setSortDropdownOpen(false); }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors hover:bg-muted ${
                    sortBy === "created_at" ? "text-foreground font-medium" : "text-muted-foreground"
                  }`}
                >
                  Date added
                </button>
                <button
                  onClick={() => { setSortBy("title"); setSortDropdownOpen(false); }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors hover:bg-muted ${
                    sortBy === "title" ? "text-foreground font-medium" : "text-muted-foreground"
                  }`}
                >
                  Name
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i}>
                <div className="skeleton aspect-video rounded-t-xl" />
                <div className="bg-white border border-t-0 border-border rounded-b-xl p-3">
                  <div className="skeleton h-4 w-2/3 mb-2" />
                  <div className="skeleton h-3 w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        ) : viewMode === "list" ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
            {projects.length === 0 && (
              <p className="col-span-full text-muted-foreground text-sm text-center py-12">
                {selectedTags.length > 0
                  ? "No projects match the selected filters."
                  : pendingProjectsCount > 0
                    ? `${pendingProjectsCount} pending project${pendingProjectsCount !== 1 ? "s" : ""}`
                    : "No projects found."}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-10">
            {competitions.map((competition) => (
              <div key={competition.id}>
                <h2 className="text-lg font-semibold text-foreground mb-4 tracking-tight">
                  {competition.name}
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {competition.projects.map((project) => (
                    <CompetitionProjectCard key={project.id} project={project} />
                  ))}
                  {competition.projects.length === 0 && (
                    <p className="col-span-full text-muted-foreground text-sm text-center py-6">
                      {competition.pending_projects_count > 0
                        ? `${competition.pending_projects_count} pending project${competition.pending_projects_count !== 1 ? "s" : ""}`
                        : "No projects in this competition."}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {competitions.length === 0 && (
              <p className="text-muted-foreground text-sm text-center py-12">
                {pendingProjectsCount > 0
                  ? `${pendingProjectsCount} pending project${pendingProjectsCount !== 1 ? "s" : ""}`
                  : "No competitions found."}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const mainImage =
    project.images?.find((img) => img.is_main) || project.images?.[0];
  const placeholderColor = getPlaceholderColor(project.id);
  const isWinner = project.won_competitions && project.won_competitions.length > 0;

  return (
    <Link
      href={`/projects/${project.id}`}
      className={`card card-interactive group ${isWinner ? "border-amber-300 ring-1 ring-amber-200" : ""}`}
    >
      <div className={`relative aspect-video ${!mainImage ? placeholderColor : "bg-slate-100"}`}>
        {mainImage && (
          <Image
            src={mainImage.url}
            alt={project.title}
            fill
            className="object-cover"
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
        {project.tags && project.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {project.tags.slice(0, 3).map((tag) => (
              <TagBadge key={tag.id} name={tag.name} color={tag.color} size="sm" />
            ))}
            {project.tags.length > 3 && (
              <span className="text-xs text-muted-foreground">+{project.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}

function CompetitionProjectCard({ project }: { project: CompetitionProject }) {
  const placeholderColor = getPlaceholderColor(project.id);

  return (
    <Link
      href={`/projects/${project.id}`}
      className="card card-interactive group"
    >
      <div className={`relative aspect-video ${!project.main_image_url ? placeholderColor : "bg-slate-100"}`}>
        {project.main_image_url && (
          <Image
            src={project.main_image_url}
            alt={project.title}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 50vw, 33vw"
          />
        )}
      </div>
      <div className="p-3.5">
        <h3 className="font-medium text-sm text-foreground truncate group-hover:text-accent transition-colors">
          {project.title || "Untitled"}
        </h3>
      </div>
    </Link>
  );
}
