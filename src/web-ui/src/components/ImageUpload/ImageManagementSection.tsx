"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { api } from "@/lib/api";
import type {
  ProjectImagesGroupedResponse,
  PurposeImageSlot,
} from "@/lib/api/images";
import { GenerationDialog } from "@/components/GenerationDialog";

type Purpose = "icon" | "main_image" | "winner_composite";

interface ImageManagementSectionProps {
  projectId: string;
  projectTitle: string;
  projectTagline: string;
}

function SlotPreview({
  label,
  slot,
  onGenerate,
  onAccept,
  onReject,
}: {
  label: string;
  slot: PurposeImageSlot;
  purpose: Purpose;
  onGenerate: () => void;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const activeImage = slot.active[0];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <button onClick={onGenerate} className="text-xs text-accent hover:underline">
          Generate
        </button>
      </div>

      {activeImage ? (
        <div className="w-16 h-16 rounded-lg overflow-hidden border border-border">
          <Image
            src={activeImage.url}
            alt={label}
            width={64}
            height={64}
            className="w-full h-full object-cover"
            unoptimized
          />
        </div>
      ) : (
        <div className="w-16 h-16 rounded-lg border-2 border-dashed border-border flex items-center justify-center">
          <span className="text-xs text-muted-foreground">None</span>
        </div>
      )}

      {/* Proposed images */}
      {slot.proposed.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {slot.proposed.map((img) => (
            <div key={img.id} className="relative group">
              <div className="w-12 h-12 rounded overflow-hidden border border-amber-300">
                <Image
                  src={img.url}
                  alt="Proposed"
                  width={48}
                  height={48}
                  className="w-full h-full object-cover"
                  unoptimized
                />
              </div>
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center gap-0.5">
                <button
                  onClick={() => onAccept(img.id)}
                  className="text-[10px] px-1 py-0.5 bg-green-500 text-white rounded"
                >
                  ✓
                </button>
                <button
                  onClick={() => onReject(img.id)}
                  className="text-[10px] px-1 py-0.5 bg-red-500 text-white rounded"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ImageManagementSection({
  projectId,
  projectTitle,
  projectTagline,
}: ImageManagementSectionProps) {
  const [images, setImages] = useState<ProjectImagesGroupedResponse | null>(null);
  const [generatingPurpose, setGeneratingPurpose] = useState<Purpose | null>(null);
  const [loading, setLoading] = useState(true);

  const loadImages = useCallback(async () => {
    try {
      const result = await api.images.getProjectImages(projectId);
      setImages(result);
    } catch {
      // Silently fail — not critical for edit page
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const handleAccept = async (imageId: string) => {
    await api.images.acceptImage(imageId);
    loadImages();
  };

  const handleReject = async (imageId: string) => {
    await api.images.rejectImage(imageId);
    loadImages();
  };

  if (loading || !images) return null;

  const hasIcon = images.icon.active.length > 0;
  const activeIcon = images.icon.active[0];

  const referenceImages = [
    ...(activeIcon
      ? [{ id: activeIcon.id, url: activeIcon.url, label: "Icon" }]
      : []),
    ...images.screenshots.active.map((s) => ({
      id: s.id,
      url: s.url,
      label: "Screenshot",
    })),
  ];

  return (
    <>
      {/* Icon missing banner */}
      {!hasIcon && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          <p className="font-medium mb-1">Icon required</p>
          <p className="text-xs">
            Upload or generate an icon to appear on the projects listing page.
          </p>
          <button
            onClick={() => setGeneratingPurpose("icon")}
            className="mt-2 text-xs font-medium text-accent hover:underline"
          >
            Generate an icon
          </button>
        </div>
      )}

      {/* Purpose image slots */}
      <div className="space-y-3 border-t border-border pt-3">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Project Images
        </p>
        <SlotPreview
          label="Icon"
          slot={images.icon}
          purpose="icon"
          onGenerate={() => setGeneratingPurpose("icon")}
          onAccept={handleAccept}
          onReject={handleReject}
        />
        <SlotPreview
          label="Main Image"
          slot={images.main_image}
          purpose="main_image"
          onGenerate={() => setGeneratingPurpose("main_image")}
          onAccept={handleAccept}
          onReject={handleReject}
        />
      </div>

      {generatingPurpose && (
        <GenerationDialog
          open={!!generatingPurpose}
          onClose={() => setGeneratingPurpose(null)}
          onAccepted={() => {
            setGeneratingPurpose(null);
            loadImages();
          }}
          projectId={projectId}
          projectTitle={projectTitle}
          projectTagline={projectTagline}
          purpose={generatingPurpose}
          referenceImages={referenceImages}
          iconImageId={activeIcon?.id}
        />
      )}
    </>
  );
}
