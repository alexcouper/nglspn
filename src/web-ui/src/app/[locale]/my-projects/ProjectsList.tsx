"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api, type Project } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import { Translatable } from "@/components/Translatable";

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations();
  const styles: Record<string, string> = {
    pending: "badge-warning",
    approved: "badge-success",
    rejected: "badge-error",
  };

  const labelKeys: Record<string, string> = {
    pending: "projects.status.pending",
    approved: "projects.status.approved",
    rejected: "projects.status.rejected",
  };

  const tKey = labelKeys[status];

  return (
    <span className={`badge ${styles[status] || "badge-neutral"}`}>
      {tKey ? <Translatable tKey={tKey}>{t(tKey)}</Translatable> : status}
    </span>
  );
}

export function ProjectsList() {
  const t = useTranslations();
  const { isReady, isLoading: authLoading } = useRequireAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isReady) return;

    let cancelled = false;

    api.myProjects.list().then(
      (projects) => {
        if (!cancelled) {
          setProjects(projects);
          setIsLoading(false);
        }
      },
      (err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load projects");
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [isReady]);

  if (authLoading || isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex gap-4">
              <div className="skeleton w-32 aspect-video rounded-lg" />
              <div className="flex-1">
                <div className="skeleton h-5 w-1/3 mb-2" />
                <div className="skeleton h-4 w-1/2 mb-2" />
                <div className="skeleton h-3 w-2/3" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
        <Link href="/" className="text-sm text-accent hover:text-accent-hover transition-colors">
          <Translatable tKey="common.backToHome">{t("common.backToHome")}</Translatable>
        </Link>
      </div>
    );
  }

  return (
    <>
      {projects.length === 0 ? (
        <div className="bg-white rounded-xl border border-border p-8 text-center">
          <p className="text-muted-foreground text-sm">
            <Translatable tKey="myProjects.empty">{t("myProjects.empty")}</Translatable>
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => {
            const mainImage = project.images?.find((img) => img.is_main) || project.images?.[0];
            const thumbUrl = mainImage ? pickVariant(mainImage.variants, "thumb") : null;
            return (
              <Link
                key={project.id}
                href={`/my-projects/${project.id}`}
                className="group block bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                <div className="flex gap-4">
                  {mainImage && (
                    <div className="relative w-32 aspect-video flex-shrink-0 rounded-lg overflow-hidden bg-slate-100">
                      {thumbUrl ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={thumbUrl}
                          alt={project.title || "Project image"}
                          className="absolute inset-0 w-full h-full object-contain"
                          loading="lazy"
                        />
                      ) : (
                        <Image
                          src={mainImage.url}
                          alt={project.title || "Project image"}
                          fill
                          className="object-contain"
                          sizes="128px"
                        />
                      )}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <h2 className="font-medium text-foreground truncate group-hover:text-accent transition-colors">
                          {project.title || t("projects.untitledProject")}
                        </h2>
                        <p className="text-muted-foreground text-xs truncate mt-0.5">
                          {project.website_url}
                        </p>
                      </div>
                      <StatusBadge status={project.status} />
                    </div>
                    {project.description && (
                      <p className="text-muted-foreground text-sm mt-2 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <div className="mt-8 text-center">
        <Link href="/submit" className="btn-primary">
          {projects.length === 0 ? (
            <Translatable tKey="myProjects.submitFirst">{t("myProjects.submitFirst")}</Translatable>
          ) : (
            <Translatable tKey="myProjects.submitNew">{t("myProjects.submitNew")}</Translatable>
          )}
        </Link>
      </div>
    </>
  );
}
