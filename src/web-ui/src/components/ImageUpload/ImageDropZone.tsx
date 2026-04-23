"use client";

import { useState, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { CloudArrowUpIcon, PhotoIcon } from "@heroicons/react/24/outline";
import { Translatable } from "@/components/Translatable";

interface ImageDropZoneProps {
  onFilesSelected: (files: FileList) => void;
  disabled?: boolean;
  maxFiles?: number;
  currentCount?: number;
}

export function ImageDropZone({
  onFilesSelected,
  disabled = false,
  maxFiles = 10,
  currentCount = 0,
}: ImageDropZoneProps) {
  const t = useTranslations();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (dragCounterRef.current === 1) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current = 0;
      setIsDragging(false);

      if (disabled) return;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        onFilesSelected(files);
      }
    },
    [disabled, onFilesSelected]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        onFilesSelected(files);
      }
      // Reset input so same file can be selected again
      e.target.value = "";
    },
    [onFilesSelected]
  );

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [disabled]);

  const remainingSlots = maxFiles - currentCount;

  return (
    <div
      className={`
        relative border-2 border-dashed rounded-lg p-8 text-center
        transition-all duration-200 cursor-pointer
        ${isDragging ? "border-accent bg-accent/10 ring-4 ring-accent/20 scale-[1.02]" : "border-border hover:border-foreground/30"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
        className="hidden"
        onChange={handleFileInput}
        disabled={disabled}
      />

      <div className="flex flex-col items-center gap-2">
        {isDragging ? (
          <CloudArrowUpIcon className="w-12 h-12 text-accent" />
        ) : (
          <PhotoIcon className="w-12 h-12 text-muted-foreground" />
        )}

        <p className="text-sm text-muted-foreground">
          {isDragging ? (
            <Translatable tKey="imageUpload.dropHere">{t("imageUpload.dropHere")}</Translatable>
          ) : (
            <Translatable tKey="imageUpload.instruction">{t("imageUpload.instruction")}</Translatable>
          )}
        </p>

        <p className="text-xs text-muted-foreground/70">
          <Translatable tKey="imageUpload.formats">{t("imageUpload.formats")}</Translatable>
        </p>
        <p className="text-xs text-muted-foreground/70">
          <Translatable tKey="imageUpload.aspectRatio">{t("imageUpload.aspectRatio")}</Translatable>
        </p>

        <p className="text-xs text-muted-foreground/50">
          {remainingSlots > 0 ? (
            <Translatable tKey="imageUpload.slotsRemaining">
              {t("imageUpload.slotsRemaining", { remaining: remainingSlots, maxFiles })}
            </Translatable>
          ) : (
            <Translatable tKey="imageUpload.maxReached">{t("imageUpload.maxReached")}</Translatable>
          )}
        </p>
      </div>
    </div>
  );
}
