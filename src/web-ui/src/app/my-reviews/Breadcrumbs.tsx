"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBreadcrumbs } from "./BreadcrumbContext";

export function Breadcrumbs() {
  const pathname = usePathname();
  const { data } = useBreadcrumbs();
  const segments = pathname.split("/").filter(Boolean);

  const isCompetitionsView = segments.length === 1;
  const isProjectsView = segments.length === 2;
  const isDetailView = segments.length === 3;

  const competitionId = segments[1];

  return (
    <nav className="mb-5 text-sm">
      <ol className="flex items-center gap-1.5 text-muted-foreground">
        <li>
          {isCompetitionsView ? (
            <span className="text-foreground font-medium">My Reviews</span>
          ) : (
            <Link href="/my-reviews" className="hover:text-foreground transition-colors">
              My Reviews
            </Link>
          )}
        </li>
        {(isProjectsView || isDetailView) && (
          <>
            <li className="text-border">/</li>
            <li>
              {isProjectsView ? (
                <span className="text-foreground font-medium">
                  {data.competitionName || "..."}
                </span>
              ) : (
                <Link
                  href={`/my-reviews/${competitionId}`}
                  className="hover:text-foreground transition-colors"
                >
                  {data.competitionName || "..."}
                </Link>
              )}
            </li>
          </>
        )}
        {isDetailView && (
          <>
            <li className="text-border">/</li>
            <li>
              <span className="text-foreground font-medium truncate max-w-[200px] inline-block align-middle">
                {data.projectTitle || "..."}
              </span>
            </li>
          </>
        )}
      </ol>
    </nav>
  );
}
