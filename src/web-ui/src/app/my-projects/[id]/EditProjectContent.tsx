"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { Project, ProjectImage } from "@/lib/api";
import { ImageDropZone, UploadProgress } from "@/components/ImageUpload";
import { ImageRoleDialog } from "@/components/ImageRoleDialog";
import { TagSidebarSelector } from "@/components/TagSidebarSelector";
import { ProjectPageLayout } from "@/components/ProjectPageLayout";
import { ProjectCompetitions } from "@/components/ProjectCompetitions";
import type { CompetitionStanding } from "@/lib/api/my-projects";
import type { SelectedTag } from "@/components/TagSelector";
import type { ProjectFormData } from "./ProjectDetail";
import { EditableProjectBanner } from "./EditableProjectBanner";
import { MyProjectArticles } from "./MyProjectArticles";
import { pickVariant, getAuthorName } from "@/lib/utils";

interface UploadProgressItem {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface EditProjectContentProps {
  project: Project;
  formData: ProjectFormData;
  onChange: (data: ProjectFormData) => void;
  onTagsChange: (tags: SelectedTag[]) => void;
  images: ProjectImage[];
  uploads: UploadProgressItem[];
  isUploading: boolean;
  onFilesSelected: (files: FileList) => void;
  onUpdateImageRoles: (
    imageId: string,
    roles: { is_main?: boolean; is_hero?: boolean; is_usage?: boolean }
  ) => void;
  onDeleteImage: (imageId: string) => void;
  iconImage: ProjectImage | null;
  onIconFilesSelected: (files: FileList) => void;
  onDeleteIcon: (imageId: string) => void;
  // Competitions live under Settings, so the standing has to come this far
  // down. Read-only data and one callback — not worth a context.
  competitionStanding: CompetitionStanding | null;
  competitionError: string;
  onEnterCompetition: (competitionId: string) => Promise<void>;
}

const MAX_IMAGES = 10;

const STATUS_STYLES: Record<string, string> = {
  draft: "badge-neutral",
  pending: "badge-warning",
  approved: "badge-success",
  rejected: "badge-error",
};

const STATUS_KEYS: Record<string, "draft" | "pending" | "approved" | "rejected"> = {
  draft: "draft",
  pending: "pending",
  approved: "approved",
  rejected: "rejected",
};

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("my-projects.editContent.status");
  const key = STATUS_KEYS[status];

  return (
    <span className={`badge ${STATUS_STYLES[status] || "badge-neutral"}`}>
      {key ? t(key) : status}
    </span>
  );
}

function RoleBadges({ image }: { image: ProjectImage }) {
  const t = useTranslations("my-projects.editContent.roleBadges");
  const badges: { role: "main" | "hero" | "usage"; color: string }[] = [];
  if (image.is_main) badges.push({ role: "main", color: "bg-accent" });
  if (image.is_hero) badges.push({ role: "hero", color: "bg-indigo-500" });
  if (image.is_usage) badges.push({ role: "usage", color: "bg-emerald-500" });
  if (badges.length === 0) return null;

  return (
    <div className="absolute top-1 right-1 flex gap-0.5">
      {badges.map((b) => (
        <span
          key={b.role}
          className={`${b.color} text-white w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center`}
        >
          {t(b.role)}
        </span>
      ))}
    </div>
  );
}

export function EditProjectContent({
  project,
  formData,
  onChange,
  onTagsChange,
  images,
  uploads,
  isUploading,
  onFilesSelected,
  onUpdateImageRoles,
  onDeleteImage,
  iconImage,
  onIconFilesSelected,
  onDeleteIcon,
  competitionStanding,
  competitionError,
  onEnterCompetition,
}: EditProjectContentProps) {
  const t = useTranslations("my-projects.editContent");
  const authorName = getAuthorName(project.creator);
  const [roleDialogImage, setRoleDialogImage] = useState<ProjectImage | null>(
    null
  );

  const handleChange = (
    field: keyof ProjectFormData,
    value: string | string[]
  ) => {
    onChange({ ...formData, [field]: value });
  };

  const handleTagsChange = (tagIds: string[], tags: SelectedTag[]) => {
    onChange({ ...formData, tag_ids: tagIds });
    onTagsChange(tags);
  };

  const galleryImages = images.filter((img) => !img.is_icon);
  const mainImage =
    galleryImages.find((img) => img.is_main) || galleryImages[0];
  const otherImages = galleryImages.filter(
    (img) => img.id !== mainImage?.id
  );

  const sidebar = (
    <>
      {/* Main image — click to open role dialog */}
      {mainImage && (
        <div
          className="relative rounded-xl overflow-hidden bg-muted cursor-pointer"
          onClick={() => setRoleDialogImage(mainImage)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={pickVariant(mainImage.variants, "medium") ?? mainImage.url}
            alt={mainImage.original_filename}
            className="w-full h-auto object-contain"
          />
          <RoleBadges image={mainImage} />
        </div>
      )}

      {/* Thumbnail grid — click to open role dialog */}
      {otherImages.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {otherImages.map((img) => (
            <div
              key={img.id}
              className="relative aspect-square rounded-lg overflow-hidden bg-muted cursor-pointer group"
              onClick={() => setRoleDialogImage(img)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pickVariant(img.variants, "thumb") ?? img.url}
                alt={img.original_filename}
                className="w-full h-full object-cover"
              />
              <RoleBadges image={img} />
              <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          ))}
        </div>
      )}

      {/* Upload drop zone */}
      <ImageDropZone
        onFilesSelected={onFilesSelected}
        disabled={isUploading || galleryImages.length >= MAX_IMAGES}
        maxFiles={MAX_IMAGES}
        currentCount={galleryImages.length}
      />
      <UploadProgress uploads={uploads} />

      {/* Tag selector */}
      <div className="pt-2">
        <TagSidebarSelector
          selectedTagIds={formData.tag_ids}
          onChange={handleTagsChange}
        />
      </div>
    </>
  );

  const tabs = [
    {
      id: "description",
      label: t("tabs.description"),
      content: (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {t("markdown")}
            </span>
          </div>
          <textarea
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="w-full min-h-[70vh] resize-y rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-foreground leading-relaxed placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
            placeholder={t("descriptionPlaceholder")}
          />
        </div>
      ),
    },
    {
      id: "articles",
      label: t("tabs.articles"),
      content: (
        <MyProjectArticles projectSlugOrId={project.slug ?? project.id} />
      ),
    },
    {
      id: "settings",
      label: t("tabs.settings"),
      content: (
        <div className="space-y-6" data-testid="settings-tab">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">{t("statusLabel")}</span>
              <StatusBadge status={project.status} />
            </div>
            <div className="text-sm text-muted-foreground">
              {t("submittedOn", {
                date: new Date(project.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                }),
              })}
            </div>
          </div>

          {competitionStanding && (
            <ProjectCompetitions
              standing={competitionStanding}
              wonCompetitionSlugs={(project.won_competitions ?? []).map(
                (won) => won.slug
              )}
              isCommunityTipoff={project.is_community_tipoff}
              onEnter={onEnterCompetition}
              error={competitionError}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <ProjectPageLayout
        banner={
          <EditableProjectBanner
            formData={formData}
            authorName={authorName}
            isTipoff={project.is_community_tipoff}
            onChange={onChange}
            iconImage={iconImage}
            onIconFilesSelected={onIconFilesSelected}
            onDeleteIcon={onDeleteIcon}
          />
        }
        sidebar={sidebar}
        tabs={tabs}
      />

      {/* Image Role Dialog */}
      {roleDialogImage && (
        <ImageRoleDialog
          image={roleDialogImage}
          projectTitle={formData.title}
          projectTagline={formData.tagline}
          projectId={project.id}
          isOpen={!!roleDialogImage}
          onClose={() => setRoleDialogImage(null)}
          onUpdateRoles={(imageId, roles) => {
            onUpdateImageRoles(imageId, roles);
            // Update the dialog's local view of the image
            const updated = images.find((img) => img.id === imageId);
            if (updated) {
              setRoleDialogImage({ ...updated, ...roles } as ProjectImage);
            }
          }}
          onDelete={onDeleteImage}
        />
      )}
    </>
  );
}
