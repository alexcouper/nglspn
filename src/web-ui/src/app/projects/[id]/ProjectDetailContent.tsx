"use client";

import { useState, useMemo, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  TrophyIcon,
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/solid";
import type { Project } from "@/lib/api";
import { TagGroup } from "@/components/TagBadge";
import { ProjectPageLayout } from "@/components/ProjectPageLayout";
import { ProjectTitleBanner } from "@/components/ProjectTitleBanner";
import { pickVariant, groupTagsByCategory } from "@/lib/utils";

interface Props {
  project: Project;
  projectId: string;
}

export function ProjectDetailContent({ project }: Props) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const tagsByCategory = useMemo(
    () => groupTagsByCategory(project.tags),
    [project.tags]
  );

  const images = project.images ?? [];
  const mainImage = images.find((img) => img.is_main) || images[0];
  const otherImages = images.filter((img) => img.id !== mainImage?.id);
  const imageCount = images.length;

  const mainImageIndex = images.findIndex(
    (img) => img.id === mainImage?.id
  );

  useEffect(() => {
    if (lightboxIndex === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightboxIndex(null);
      if (e.key === "ArrowLeft") {
        setLightboxIndex((prev) =>
          prev !== null ? (prev - 1 + imageCount) % imageCount : null
        );
      }
      if (e.key === "ArrowRight") {
        setLightboxIndex((prev) =>
          prev !== null ? (prev + 1) % imageCount : null
        );
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [lightboxIndex, imageCount]);

  const sidebar = (
    <>
      {/* Mobile: stacked image preview */}
      {mainImage && (
        <div className="lg:hidden flex justify-center">
          <div
            className="w-[280px] cursor-pointer"
            onClick={() => setLightboxIndex(mainImageIndex)}
          >
            <div className="relative">
              {images[2] && (
                <div className="absolute inset-0 rounded-xl overflow-hidden border border-border transform translate-x-3 -translate-y-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={pickVariant(images[2].variants, "thumb") ?? images[2].url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              {images[1] && (
                <div className="absolute inset-0 rounded-xl overflow-hidden border border-border transform translate-x-1.5 -translate-y-1.5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={pickVariant(images[1].variants, "thumb") ?? images[1].url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="relative rounded-xl overflow-hidden bg-muted border border-border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={
                    pickVariant(mainImage.variants, "thumb") ??
                    mainImage.url
                  }
                  alt={project.title}
                  className="w-full h-auto object-contain"
                />
              </div>
            </div>
            {imageCount > 1 && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                {imageCount} images
              </p>
            )}
          </div>
        </div>
      )}

      {/* Desktop: main image */}
      {mainImage && (
        <div
          className="hidden lg:block rounded-xl overflow-hidden bg-muted cursor-pointer hover:ring-2 hover:ring-accent/50 transition-all"
          onClick={() => setLightboxIndex(mainImageIndex)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={
              pickVariant(mainImage.variants, "medium") ??
              mainImage.url
            }
            alt={project.title}
            className="w-full h-auto object-contain"
          />
        </div>
      )}

      {/* Thumbnail grid — desktop only */}
      {otherImages.length > 0 && (
        <div className="hidden lg:grid grid-cols-3 gap-2">
          {otherImages.map((img) => {
            const idx = images.findIndex((i) => i.id === img.id);
            return (
              <div
                key={img.id}
                className="aspect-square rounded-lg overflow-hidden bg-muted cursor-pointer hover:ring-2 hover:ring-accent/50 transition-all"
                onClick={() => setLightboxIndex(idx)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={
                    pickVariant(img.variants, "thumb") ?? img.url
                  }
                  alt={img.original_filename}
                  className="w-full h-full object-cover"
                />
              </div>
            );
          })}
        </div>
      )}

      {/* Tags — desktop only */}
      {tagsByCategory.length > 0 && (
        <div className="hidden lg:block space-y-4">
          {tagsByCategory.map((group) => (
            <TagGroup
              key={group.categoryName}
              categoryName={group.categoryName}
              tags={group.tags}
            />
          ))}
        </div>
      )}

      {/* Submitted date — desktop only */}
      <p className="hidden lg:block text-xs text-muted-foreground">
        Submitted{" "}
        {new Date(project.created_at).toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </p>
    </>
  );

  const winnerBanner =
    project.won_competitions && project.won_competitions.length > 0 ? (
      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-2">
        <TrophyIcon className="w-5 h-5 text-amber-500 flex-shrink-0" />
        <p className="text-amber-800 text-sm">
          Winner of{" "}
          {project.won_competitions.map((comp, i) => (
            <span key={comp.slug}>
              {i > 0 && ", "}
              <Link
                href={`/competitions/${comp.slug}`}
                className="font-medium underline hover:text-amber-900 transition-colors"
              >
                {comp.name}
              </Link>
            </span>
          ))}
        </p>
      </div>
    ) : undefined;

  const tabs = [
    {
      id: "description",
      label: "Description",
      content: (
        <article className="markdown">
          <ReactMarkdown>{project.description}</ReactMarkdown>
        </article>
      ),
    },
  ];

  return (
    <>
      <ProjectPageLayout
        banner={<ProjectTitleBanner project={project} />}
        sidebar={sidebar}
        tabs={tabs}
        winnerBanner={winnerBanner}
      />

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={() => setLightboxIndex(null)}
        >
          <button
            onClick={() => setLightboxIndex(null)}
            className="absolute top-4 right-4 p-2 text-white/70 hover:text-white transition-colors"
          >
            <XMarkIcon className="w-8 h-8" />
          </button>
          {images.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setLightboxIndex((prev) =>
                  prev !== null
                    ? (prev - 1 + imageCount) % imageCount
                    : null
                );
              }}
              className="absolute left-4 p-2 text-white/70 hover:text-white transition-colors"
            >
              <ChevronLeftIcon className="w-10 h-10" />
            </button>
          )}
          <div
            className="relative max-w-[90vw] max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {(() => {
              const src =
                pickVariant(images[lightboxIndex].variants, "large") ??
                images[lightboxIndex].url;
              return src ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={src}
                  alt={images[lightboxIndex].original_filename}
                  className="max-w-[90vw] max-h-[90vh] object-contain"
                />
              ) : (
                <Image
                  src={images[lightboxIndex].url}
                  alt={images[lightboxIndex].original_filename}
                  width={images[lightboxIndex].width || 1200}
                  height={images[lightboxIndex].height || 800}
                  className="max-w-[90vw] max-h-[90vh] object-contain"
                  priority
                />
              );
            })()}
          </div>
          {images.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setLightboxIndex((prev) =>
                  prev !== null ? (prev + 1) % imageCount : null
                );
              }}
              className="absolute right-4 p-2 text-white/70 hover:text-white transition-colors"
            >
              <ChevronRightIcon className="w-10 h-10" />
            </button>
          )}
          {images.length > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
              {lightboxIndex + 1} / {images.length}
            </div>
          )}
        </div>
      )}
    </>
  );
}
