"use client";

import { useCallback, useRef, useState } from "react";
import { PhotoIcon, XMarkIcon } from "@heroicons/react/24/outline";
import type { ProjectImage } from "@/lib/api";
import { pickVariant } from "@/lib/utils";

interface Props {
  heroImage: ProjectImage | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
  onClear: () => void;
}

export function HeroImageUploader({
  heroImage,
  isUploading,
  onUpload,
  onClear,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      onUpload(files[0]);
    },
    [onUpload],
  );

  if (heroImage) {
    const src =
      pickVariant(heroImage.variants, "large") ?? heroImage.url;
    return (
      <div className="relative rounded-lg overflow-hidden border border-border bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={heroImage.original_filename}
          className="w-full max-h-80 object-cover"
        />
        <button
          onClick={onClear}
          title="Remove hero image"
          className="absolute top-2 right-2 p-1.5 rounded-full bg-white/90 text-foreground hover:bg-white shadow"
        >
          <XMarkIcon className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      onDragEnter={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setIsDragging(false);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragging
          ? "border-accent bg-accent/10"
          : "border-border hover:border-foreground/30"
      } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <PhotoIcon className="w-10 h-10" />
        <p className="text-sm">
          <span className="text-accent font-medium">Click to upload</span>{" "}
          or drag a hero image
        </p>
        <p className="text-xs text-muted-foreground/70">
          PNG, JPG, WebP, GIF up to 10MB
        </p>
        {isUploading && (
          <p className="text-xs text-muted-foreground">Uploading…</p>
        )}
      </div>
    </div>
  );
}
