"use client";

import type { Project, ProjectImage } from "@/lib/api";
import { ImageDropZone, UploadProgress } from "@/components/ImageUpload";
import { TagSidebarSelector } from "@/components/TagSidebarSelector";
import { ProjectPageLayout } from "@/components/ProjectPageLayout";
import type { SelectedTag } from "@/components/TagSelector";
import type { ProjectFormData } from "./ProjectDetail";
import { EditableProjectBanner } from "./EditableProjectBanner";
import { StarIcon, TrashIcon } from "@heroicons/react/24/outline";
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid";
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
  onSetMainImage: (imageId: string) => void;
  onDeleteImage: (imageId: string) => void;
}

const MAX_IMAGES = 10;

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "badge-warning",
    approved: "badge-success",
    rejected: "badge-error",
  };

  const labels: Record<string, string> = {
    pending: "Pending Review",
    approved: "Approved",
    rejected: "Rejected",
  };

  return (
    <span className={`badge ${styles[status] || "badge-neutral"}`}>
      {labels[status] || status}
    </span>
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
  onSetMainImage,
  onDeleteImage,
}: EditProjectContentProps) {
  const authorName = getAuthorName(project.owner);

  const handleChange = (field: keyof ProjectFormData, value: string | string[]) => {
    onChange({ ...formData, [field]: value });
  };

  const handleTagsChange = (tagIds: string[], tags: SelectedTag[]) => {
    onChange({ ...formData, tag_ids: tagIds });
    onTagsChange(tags);
  };

  const mainImage = images.find((img) => img.is_main) || images[0];
  const otherImages = images.filter((img) => img.id !== mainImage?.id);

  const sidebar = (
    <>
      {/* Main image with edit controls */}
      {mainImage && (
        <div className="relative rounded-xl overflow-hidden bg-muted">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={pickVariant(mainImage.variants, "medium") ?? mainImage.url}
            alt={mainImage.original_filename}
            className="w-full h-auto object-contain"
          />
          <div className="absolute top-2 right-2 flex gap-1">
            <span className="bg-accent text-white px-2 py-1 rounded text-xs font-medium flex items-center gap-1">
              <StarIconSolid className="w-3 h-3" />
              Main
            </span>
            <button
              onClick={() => onDeleteImage(mainImage.id)}
              className="p-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
              title="Delete image"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Thumbnail grid — matches view mode 3-col layout */}
      {otherImages.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {otherImages.map((img) => (
            <div
              key={img.id}
              className="relative aspect-square rounded-lg overflow-hidden bg-muted group"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pickVariant(img.variants, "thumb") ?? img.url}
                alt={img.original_filename}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <button
                  onClick={() => onSetMainImage(img.id)}
                  className="p-2 bg-white rounded-full hover:bg-muted transition-colors"
                  title="Set as main image"
                >
                  <StarIcon className="w-4 h-4 text-foreground" />
                </button>
                <button
                  onClick={() => onDeleteImage(img.id)}
                  className="p-2 bg-white rounded-full hover:bg-muted transition-colors"
                  title="Delete image"
                >
                  <TrashIcon className="w-4 h-4 text-red-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload drop zone */}
      <ImageDropZone
        onFilesSelected={onFilesSelected}
        disabled={isUploading || images.length >= MAX_IMAGES}
        maxFiles={MAX_IMAGES}
        currentCount={images.length}
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
      label: "Description",
      content: (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              Markdown
            </span>
          </div>
          <textarea
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="w-full min-h-[70vh] resize-y rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-foreground leading-relaxed placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
            placeholder="Tell us about your project..."
          />
        </div>
      ),
    },
    {
      id: "settings",
      label: "Settings",
      content: (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Status:</span>
            <StatusBadge status={project.status} />
          </div>
          <div className="text-sm text-muted-foreground">
            Submitted{" "}
            {new Date(project.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </div>
        </div>
      ),
    },
  ];

  return (
    <ProjectPageLayout
      banner={
        <EditableProjectBanner
          formData={formData}
          authorName={authorName}
          onChange={onChange}
        />
      }
      sidebar={sidebar}
      tabs={tabs}
    />
  );
}
