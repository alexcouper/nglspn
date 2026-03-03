"use client";

import type { ProjectFormData } from "./ProjectDetail";

interface EditableProjectBannerProps {
  formData: ProjectFormData;
  authorName: string;
  onChange: (data: ProjectFormData) => void;
}

export function EditableProjectBanner({
  formData,
  authorName,
  onChange,
}: EditableProjectBannerProps) {
  const handleChange = (field: keyof ProjectFormData, value: string) => {
    onChange({ ...formData, [field]: value });
  };

  return (
    <section className="relative bg-white border-b border-border py-10 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto">
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
    </section>
  );
}
