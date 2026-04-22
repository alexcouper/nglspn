"use client";

import { useRef } from "react";
import { CameraIcon, XMarkIcon } from "@heroicons/react/24/outline";
import type { ProjectImage } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import type { ProjectFormData } from "./ProjectDetail";

interface EditableProjectBannerProps {
  formData: ProjectFormData;
  authorName: string;
  onChange: (data: ProjectFormData) => void;
  iconImage?: ProjectImage | null;
  onIconFilesSelected?: (files: FileList) => void;
  onDeleteIcon?: (imageId: string) => void;
}

export function EditableProjectBanner({
  formData,
  authorName,
  onChange,
  iconImage,
  onIconFilesSelected,
  onDeleteIcon,
}: EditableProjectBannerProps) {
  const iconInputRef = useRef<HTMLInputElement>(null);

  const handleChange = (field: keyof ProjectFormData, value: string) => {
    onChange({ ...formData, [field]: value });
  };

  const handleIconClick = () => {
    iconInputRef.current?.click();
  };

  const handleIconFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onIconFilesSelected?.(e.target.files);
    }
    // Reset so the same file can be re-selected
    e.target.value = "";
  };

  const iconUrl = iconImage
    ? pickVariant(iconImage.variants, "thumb") ?? iconImage.url
    : null;

  return (
    <section className="relative bg-white border-b border-border py-10 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto flex gap-4 items-start">
        {/* Icon slot */}
        <div className="shrink-0">
          {iconUrl ? (
            <div className="relative group">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={iconUrl}
                alt="Project icon"
                className="w-14 h-14 rounded-lg object-cover cursor-pointer border border-border"
                onClick={handleIconClick}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (iconImage) onDeleteIcon?.(iconImage.id);
                }}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <XMarkIcon className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleIconClick}
              className="w-14 h-14 rounded-lg border-2 border-dashed border-border hover:border-accent flex items-center justify-center text-muted-foreground hover:text-accent transition-colors"
              title="Upload project icon (256x256 recommended)"
            >
              <CameraIcon className="w-5 h-5" />
            </button>
          )}
          <input
            ref={iconInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleIconFileChange}
            className="hidden"
          />
        </div>

        {/* Title and fields */}
        <div className="flex-1 min-w-0">
          <input
            type="text"
            value={formData.title}
            onChange={(e) => handleChange("title", e.target.value)}
            placeholder="Project Title"
            className="w-full text-2xl sm:text-3xl font-semibold text-foreground tracking-tight bg-transparent border-0 border-b border-dashed border-border outline-none placeholder:text-muted-foreground/50 focus:ring-0 focus:border-accent px-0 py-1 transition-colors"
          />
          <input
            type="text"
            value={formData.tagline}
            onChange={(e) => handleChange("tagline", e.target.value)}
            placeholder="A short tagline for your project"
            maxLength={200}
            className="w-full text-foreground text-base mt-1 bg-transparent border-0 border-b border-dashed border-border outline-none placeholder:text-muted-foreground/50 focus:ring-0 focus:border-accent px-0 py-1 transition-colors"
          />
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground mt-3">
            <span className="text-foreground">{authorName}</span>
            <span className="text-border">&middot;</span>
            <input
              type="url"
              value={formData.website_url}
              onChange={(e) => handleChange("website_url", e.target.value)}
              placeholder="https://your-project.com"
              className="bg-transparent border-0 border-b border-dashed border-border outline-none placeholder:text-muted-foreground/50 focus:ring-0 focus:border-accent px-0 py-1 min-w-0 flex-1 transition-colors"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
