"use client";

import type { Project, ProjectImage } from "@/lib/api";
import { ImageDropZone, ImageGallery, UploadProgress } from "@/components/ImageUpload";
import { TagSidebarSelector } from "@/components/TagSidebarSelector";
import type { SelectedTag } from "@/components/TagSelector";

export interface ProjectFormData {
  title: string;
  website_url: string;
  description: string;
  tag_ids: string[];
}

interface UploadProgressItem {
  imageId: string;
  filename: string;
  progress: number;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  error?: string;
}

interface EditProjectDetailProps {
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

export function EditProjectDetail({
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
}: EditProjectDetailProps) {
  const handleChange = (field: keyof ProjectFormData, value: string | string[]) => {
    onChange({ ...formData, [field]: value });
  };

  const handleTagsChange = (tagIds: string[], tags: SelectedTag[]) => {
    onChange({ ...formData, tag_ids: tagIds });
    onTagsChange(tags);
  };

  const MAX_IMAGES = 10;

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      <div className="flex-1 space-y-5 min-w-0">
        <div>
          <label htmlFor="title" className="label">Project Title</label>
          <input
            id="title"
            type="text"
            value={formData.title}
            onChange={(e) => handleChange("title", e.target.value)}
            className="input"
            placeholder="My Awesome Project"
          />
        </div>

        <div>
          <label htmlFor="website_url" className="label">Project URL</label>
          <input
            id="website_url"
            type="url"
            value={formData.website_url}
            onChange={(e) => handleChange("website_url", e.target.value)}
            className="input"
            placeholder="https://your-project.com"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="description" className="label mb-0">Description</label>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              Markdown
            </span>
          </div>
          <textarea
            id="description"
            rows={6}
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="input resize-none"
            placeholder="Tell us about your project..."
          />
        </div>

        <div>
          <label className="label">Project Images</label>
          <ImageGallery
            images={images}
            editable
            onSetMain={onSetMainImage}
            onDelete={onDeleteImage}
          />
          <div className="mt-3">
            <ImageDropZone
              onFilesSelected={onFilesSelected}
              disabled={isUploading || images.length >= MAX_IMAGES}
              maxFiles={MAX_IMAGES}
              currentCount={images.length}
            />
          </div>
          <UploadProgress uploads={uploads} />
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border">
          <span>Status: <span className="capitalize text-foreground">{project.status}</span></span>
          <span>
            Submitted:{" "}
            {new Date(project.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>
      </div>

      <div className="lg:w-72 lg:sticky lg:top-24 lg:self-start">
        <TagSidebarSelector
          selectedTagIds={formData.tag_ids}
          onChange={handleTagsChange}
        />
      </div>
    </div>
  );
}
