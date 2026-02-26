"use client";

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import { StarIcon, TrashIcon, XMarkIcon, ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid";
import type { ProjectImage } from "@/lib/api";

interface ImageGalleryProps {
  images: ProjectImage[];
  editable?: boolean;
  onSetMain?: (imageId: string) => void;
  onDelete?: (imageId: string) => void;
}

export function ImageGallery({
  images,
  editable = false,
  onSetMain,
  onDelete,
}: ImageGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const openLightbox = useCallback((index: number) => {
    if (!editable) {
      setLightboxIndex(index);
    }
  }, [editable]);

  const closeLightbox = useCallback(() => {
    setLightboxIndex(null);
  }, []);

  const goToPrevious = useCallback(() => {
    if (lightboxIndex !== null) {
      setLightboxIndex((lightboxIndex - 1 + images.length) % images.length);
    }
  }, [lightboxIndex, images.length]);

  const goToNext = useCallback(() => {
    if (lightboxIndex !== null) {
      setLightboxIndex((lightboxIndex + 1) % images.length);
    }
  }, [lightboxIndex, images.length]);

  // Handle keyboard navigation
  useEffect(() => {
    if (lightboxIndex === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeLightbox();
      if (e.key === "ArrowLeft") goToPrevious();
      if (e.key === "ArrowRight") goToNext();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [lightboxIndex, closeLightbox, goToPrevious, goToNext]);

  if (images.length === 0) {
    return null;
  }

  const mainImage = images.find((img) => img.is_main) || images[0];
  const otherImages = images.filter((img) => img.id !== mainImage?.id);
  const mainImageIndex = images.findIndex((img) => img.id === mainImage?.id);

  return (
    <div className="space-y-4">
      {/* Main Image */}
      {mainImage && (
        <div
          className={`relative aspect-video rounded-xl overflow-hidden bg-muted ${!editable ? "cursor-pointer" : ""}`}
          onClick={() => openLightbox(mainImageIndex)}
        >
          <Image
            src={mainImage.url}
            alt="Main project image"
            fill
            className="object-contain"
            sizes="(max-width: 768px) 100vw, 50vw"
            priority
          />
          {editable && (
            <div className="absolute top-2 right-2 flex gap-1">
              <span className="bg-accent text-white px-2 py-1 rounded text-xs font-medium flex items-center gap-1">
                <StarIconSolid className="w-3 h-3" />
                Main
              </span>
              <button
                onClick={() => onDelete?.(mainImage.id)}
                className="p-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                title="Delete image"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Additional Images */}
      {otherImages.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {otherImages.map((image) => {
            const imageIndex = images.findIndex((img) => img.id === image.id);
            return (
              <div
                key={image.id}
                className={`relative w-20 h-20 flex-shrink-0 rounded-xl overflow-hidden bg-muted group ${!editable ? "cursor-pointer hover:ring-2 hover:ring-accent/50" : ""}`}
                onClick={() => openLightbox(imageIndex)}
              >
                <Image
                  src={image.url}
                  alt={image.original_filename}
                  fill
                  className="object-cover"
                  sizes="80px"
                />
                {editable && (
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSetMain?.(image.id);
                      }}
                      className="p-2 bg-white rounded-full hover:bg-muted transition-colors"
                      title="Set as main image"
                    >
                      <StarIcon className="w-4 h-4 text-foreground" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete?.(image.id);
                      }}
                      className="p-2 bg-white rounded-full hover:bg-muted transition-colors"
                      title="Delete image"
                    >
                      <TrashIcon className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Lightbox Dialog */}
      {lightboxIndex !== null && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
        >
          {/* Close button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 p-2 text-white/70 hover:text-white transition-colors"
            title="Close (Esc)"
          >
            <XMarkIcon className="w-8 h-8" />
          </button>

          {/* Previous button */}
          {images.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                goToPrevious();
              }}
              className="absolute left-4 p-2 text-white/70 hover:text-white transition-colors"
              title="Previous (Left Arrow)"
            >
              <ChevronLeftIcon className="w-10 h-10" />
            </button>
          )}

          {/* Image */}
          <div
            className="relative max-w-[90vw] max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <Image
              src={images[lightboxIndex].url}
              alt={images[lightboxIndex].original_filename}
              width={images[lightboxIndex].width || 1200}
              height={images[lightboxIndex].height || 800}
              className="max-w-[90vw] max-h-[90vh] object-contain"
              priority
            />
          </div>

          {/* Next button */}
          {images.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                goToNext();
              }}
              className="absolute right-4 p-2 text-white/70 hover:text-white transition-colors"
              title="Next (Right Arrow)"
            >
              <ChevronRightIcon className="w-10 h-10" />
            </button>
          )}

          {/* Image counter */}
          {images.length > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
              {lightboxIndex + 1} / {images.length}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
