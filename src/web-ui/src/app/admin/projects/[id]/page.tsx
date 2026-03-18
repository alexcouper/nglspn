"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { api } from "@/lib/api";
import type {
  ProjectImagesGroupedResponse,
  PurposeImageSlot,
} from "@/lib/api/images";
import { GenerationDialog } from "@/components/GenerationDialog";

type Purpose = "icon" | "main_image" | "winner_composite";

function ImageSlot({
  label,
  slot,
  purpose,
  onGenerate,
  onAccept,
  onReject,
}: {
  label: string;
  slot: PurposeImageSlot;
  purpose: Purpose;
  onGenerate: (purpose: Purpose) => void;
  onAccept: (imageId: string) => void;
  onReject: (imageId: string) => void;
}) {
  const activeImage = slot.active[0];

  return (
    <div className="bg-white rounded-xl border border-border p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">{label}</h3>
        <button
          onClick={() => onGenerate(purpose)}
          className="btn-secondary text-xs"
        >
          Generate
        </button>
      </div>

      {/* Active image */}
      {activeImage ? (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">Active</p>
          <div className="w-32 h-32 rounded-lg overflow-hidden border border-border">
            <Image
              src={activeImage.url}
              alt={`Active ${label}`}
              width={128}
              height={128}
              className="w-full h-full object-cover"
              unoptimized
            />
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground mb-3">No active image</p>
      )}

      {/* Proposed images */}
      {slot.proposed.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">
            Proposed ({slot.proposed.length})
          </p>
          <div className="flex gap-2 flex-wrap">
            {slot.proposed.map((img) => (
              <div key={img.id} className="relative group">
                <div className="w-24 h-24 rounded-lg overflow-hidden border border-amber-300">
                  <Image
                    src={img.url}
                    alt="Proposed"
                    width={96}
                    height={96}
                    className="w-full h-full object-cover"
                    unoptimized
                  />
                </div>
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-1">
                  <button
                    onClick={() => onAccept(img.id)}
                    className="px-2 py-1 bg-green-500 text-white text-xs rounded"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => onReject(img.id)}
                    className="px-2 py-1 bg-red-500 text-white text-xs rounded"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ScreenshotsSlot({ slot }: { slot: PurposeImageSlot }) {
  if (slot.active.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-foreground mb-3">
          Screenshots
        </h3>
        <p className="text-sm text-muted-foreground">No screenshots uploaded</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-border p-5">
      <h3 className="text-sm font-semibold text-foreground mb-3">
        Screenshots ({slot.active.length})
      </h3>
      <div className="flex gap-2 flex-wrap">
        {slot.active.map((img) => (
          <div
            key={img.id}
            className="w-24 h-24 rounded-lg overflow-hidden border border-border"
          >
            <Image
              src={img.url}
              alt="Screenshot"
              width={96}
              height={96}
              className="w-full h-full object-cover"
              unoptimized
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AdminProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [images, setImages] = useState<ProjectImagesGroupedResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generatingPurpose, setGeneratingPurpose] = useState<Purpose | null>(
    null
  );

  const loadImages = useCallback(async () => {
    try {
      const result = await api.admin.getProjectImages(projectId);
      setImages(result);
    } catch {
      setError("Failed to load project images");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const handleAccept = async (imageId: string) => {
    try {
      await api.images.acceptImage(imageId);
      loadImages();
    } catch {
      setError("Failed to accept image");
    }
  };

  const handleReject = async (imageId: string) => {
    try {
      await api.images.rejectImage(imageId);
      loadImages();
    } catch {
      setError("Failed to reject image");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !images) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  const screenshots =
    images?.screenshots.active.map((s) => ({
      id: s.id,
      url: s.url,
    })) ?? [];

  const activeIcon = images?.icon.active[0];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link
          href="/admin/projects"
          className="text-sm text-accent hover:underline"
        >
          &larr; Back to projects
        </Link>
      </div>

      <h1 className="text-2xl font-semibold text-foreground mb-6">
        Image Management
      </h1>

      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {images && (
          <>
            <ImageSlot
              label="Icon"
              slot={images.icon}
              purpose="icon"
              onGenerate={setGeneratingPurpose}
              onAccept={handleAccept}
              onReject={handleReject}
            />
            <ImageSlot
              label="Main Image"
              slot={images.main_image}
              purpose="main_image"
              onGenerate={setGeneratingPurpose}
              onAccept={handleAccept}
              onReject={handleReject}
            />
            <ScreenshotsSlot slot={images.screenshots} />
            <ImageSlot
              label="Winner Composite"
              slot={images.winner_composite}
              purpose="winner_composite"
              onGenerate={setGeneratingPurpose}
              onAccept={handleAccept}
              onReject={handleReject}
            />
          </>
        )}
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
          projectTitle=""
          projectTagline=""
          purpose={generatingPurpose}
          screenshots={screenshots}
          iconImageId={activeIcon?.id}
        />
      )}
    </div>
  );
}
