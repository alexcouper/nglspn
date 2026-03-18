"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { api } from "@/lib/api";
import type { ProposedImageResponse } from "@/lib/api/images";

type Purpose = "icon" | "main_image" | "winner_composite";
type DeviceFrame = "mobile" | "laptop" | "watch";

interface ReferenceImage {
  id: string;
  url: string;
  label?: string;
}

interface GenerationDialogProps {
  open: boolean;
  onClose: () => void;
  onAccepted: (image: ProposedImageResponse) => void;
  projectId: string;
  projectTitle: string;
  projectTagline: string;
  purpose: Purpose;
  referenceImages?: ReferenceImage[];
  iconImageId?: string;
}

type DialogState =
  | "editing"
  | "generating"
  | "selecting"
  | "accepting";

function getDefaultPrompt(
  purpose: Purpose,
  title: string,
  tagline: string,
  options?: { deviceFrame?: DeviceFrame; hasReference?: boolean }
): string {
  const ref = options?.hasReference
    ? " Use the provided reference image as the basis for the composition."
    : "";
  switch (purpose) {
    case "icon":
      return `A clean, modern app icon for "${title}" - ${tagline}. Minimal style, vibrant colors, no text.${ref}`;
    case "main_image":
      if (options?.deviceFrame) {
        const device =
          options.deviceFrame === "mobile"
            ? "a smartphone"
            : options.deviceFrame === "laptop"
              ? "a laptop"
              : "a smartwatch";
        return `${device} displaying the "${title}" app, showing the main interface. Clean desk setting, professional photography.${ref}`;
      }
      return `An abstract conceptual illustration representing "${title}" - ${tagline}. Modern, clean aesthetic.${ref}`;
    case "winner_composite":
      return `A golden trophy with the app icon displayed on it, celebration confetti, dramatic lighting, award ceremony.`;
  }
}

const POLL_INTERVAL = 2000;

export function GenerationDialog({
  open,
  onClose,
  onAccepted,
  projectId,
  projectTitle,
  projectTagline,
  purpose,
  referenceImages = [],
  iconImageId,
}: GenerationDialogProps) {
  const defaultDeviceFrame: DeviceFrame = "laptop";
  const [state, setState] = useState<DialogState>("editing");
  const [prompt, setPrompt] = useState(
    getDefaultPrompt(purpose, projectTitle, projectTagline)
  );
  const [numVariants, setNumVariants] = useState(2);
  const [selectedReference, setSelectedReference] = useState<string | null>(
    null
  );
  const [deviceFrame, setDeviceFrame] = useState<DeviceFrame>(defaultDeviceFrame);
  const [generatedImages, setGeneratedImages] = useState<
    ProposedImageResponse[]
  >([]);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [error, setError] = useState("");
  const overlayRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isWinnerComposite = purpose === "winner_composite";
  const showReferences = purpose === "main_image" && referenceImages.length > 0;

  // Manage body scroll and cleanup
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [open]);

  // ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open && state === "editing") onClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, state, onClose]);

  const startPolling = useCallback((requestId: string) => {
    const poll = async () => {
      try {
        const status = await api.images.getGenerationStatus(requestId);
        if (status.status === "completed") {
          setGeneratedImages(status.images);
          if (status.images.length === 1) {
            setSelectedImage(status.images[0].id);
          }
          setState("selecting");
        } else if (status.status === "failed") {
          setError(status.error_message || "Generation failed");
          setState("editing");
        } else {
          pollRef.current = setTimeout(poll, POLL_INTERVAL);
        }
      } catch {
        setError("Failed to check generation status");
        setState("editing");
      }
    };
    void poll();
  }, []);

  const handleGenerate = async () => {
    setError("");
    setState("generating");

    try {
      const body: {
        project_id: string;
        purpose: string;
        prompt_text: string;
        num_variants: number;
        device_frame?: string;
        reference_image_id?: string;
      } = {
        project_id: projectId,
        purpose,
        prompt_text: prompt,
        num_variants: numVariants,
      };

      if (selectedReference) {
        body.reference_image_id = selectedReference;
        if (purpose === "main_image") {
          body.device_frame = deviceFrame;
        }
      }

      if (purpose === "winner_composite" && iconImageId) {
        body.reference_image_id = iconImageId;
      }

      const result = await api.images.generate(body);
      startPolling(result.generation_request_id);
    } catch {
      setError("Failed to start generation");
      setState("editing");
    }
  };

  const handleAccept = async () => {
    if (!selectedImage) return;
    setState("accepting");
    try {
      const accepted = await api.images.acceptImage(selectedImage);
      onAccepted(accepted);
      onClose();
    } catch {
      setError("Failed to accept image");
      setState("selecting");
    }
  };

  if (!open) return null;

  const purposeLabel =
    purpose === "icon"
      ? "Icon"
      : purpose === "main_image"
        ? "Main Image"
        : "Winner Composite";

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]"
      onClick={(e) => {
        if (e.target === overlayRef.current && state === "editing") onClose();
      }}
    >
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />

      <div className="relative w-full max-w-2xl bg-white rounded-xl shadow-xl animate-fade-in max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3 sticky top-0 bg-white rounded-t-xl z-10">
          <h2 className="text-base font-semibold text-foreground">
            Generate {purposeLabel} for &ldquo;{projectTitle}&rdquo;
          </h2>
          <button
            onClick={onClose}
            disabled={state === "generating" || state === "accepting"}
            className="text-muted-foreground hover:text-foreground transition-colors p-1 -mr-1"
            aria-label="Close"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </div>

        <div className="px-6 pb-6 space-y-4">
          {/* Reference image selector */}
          {showReferences && state === "editing" && (
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Reference Image (optional)
              </label>
              <div className="flex gap-2 overflow-x-auto pb-2">
                <button
                  onClick={() => {
                    setSelectedReference(null);
                    setPrompt(
                      getDefaultPrompt(purpose, projectTitle, projectTagline)
                    );
                  }}
                  className={`flex-shrink-0 w-20 h-20 rounded-lg border-2 transition-colors flex items-center justify-center text-xs text-muted-foreground ${
                    selectedReference === null
                      ? "border-accent bg-accent/5"
                      : "border-border hover:border-muted-foreground"
                  }`}
                >
                  None
                </button>
                {referenceImages.map((ref) => (
                  <button
                    key={ref.id}
                    onClick={() => {
                      setSelectedReference(ref.id);
                      setPrompt(
                        getDefaultPrompt(purpose, projectTitle, projectTagline, {
                          deviceFrame: purpose === "main_image" ? deviceFrame : undefined,
                          hasReference: true,
                        })
                      );
                    }}
                    className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-colors relative ${
                      selectedReference === ref.id
                        ? "border-accent"
                        : "border-border hover:border-muted-foreground"
                    }`}
                  >
                    <Image
                      src={ref.url}
                      alt={ref.label || "Reference"}
                      width={80}
                      height={80}
                      className="w-full h-full object-cover"
                      unoptimized
                    />
                    {ref.label && (
                      <span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] text-center py-0.5">
                        {ref.label}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Device frame picker — only for main_image with a reference selected */}
              {purpose === "main_image" && selectedReference && (
                <>
                  <label className="block text-sm font-medium text-foreground mt-3 mb-2">
                    Device Frame
                  </label>
                  <div className="flex gap-2">
                    {(["mobile", "laptop", "watch"] as DeviceFrame[]).map(
                      (frame) => (
                        <button
                          key={frame}
                          onClick={() => {
                            setDeviceFrame(frame);
                            setPrompt(
                              getDefaultPrompt(
                                purpose,
                                projectTitle,
                                projectTagline,
                                { deviceFrame: frame, hasReference: true }
                              )
                            );
                          }}
                          className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                            deviceFrame === frame
                              ? "bg-accent text-white border-accent"
                              : "bg-white text-foreground border-border hover:border-muted-foreground"
                          }`}
                        >
                          {frame.charAt(0).toUpperCase() + frame.slice(1)}
                        </button>
                      )
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={
                isWinnerComposite ||
                state === "generating" ||
                state === "accepting"
              }
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm text-foreground bg-white resize-none focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent disabled:opacity-60 disabled:bg-muted"
            />
            {isWinnerComposite && (
              <p className="text-xs text-muted-foreground mt-1">
                Winner composite prompts cannot be customized.
              </p>
            )}
          </div>

          {/* Variant count */}
          {state === "editing" && (
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Variants
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4].map((n) => (
                  <button
                    key={n}
                    onClick={() => setNumVariants(n)}
                    className={`w-10 h-10 rounded-lg text-sm font-medium border transition-colors ${
                      numVariants === n
                        ? "bg-accent text-white border-accent"
                        : "bg-white text-foreground border-border hover:border-muted-foreground"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Generate button */}
          {state === "editing" && (
            <button
              onClick={handleGenerate}
              disabled={!prompt.trim()}
              className="btn-primary w-full text-sm disabled:opacity-50"
            >
              Generate
            </button>
          )}

          {/* Generating spinner */}
          {state === "generating" && (
            <div className="flex flex-col items-center py-8 gap-3">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-muted-foreground">
                Generating images...
              </p>
            </div>
          )}

          {/* Variant selection grid */}
          {state === "selecting" && (
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Select an image to use:
              </p>
              <div
                className={`grid gap-3 ${
                  generatedImages.length === 1
                    ? "grid-cols-1"
                    : "grid-cols-2"
                }`}
              >
                {generatedImages.map((img) => (
                  <button
                    key={img.id}
                    onClick={() => setSelectedImage(img.id)}
                    className={`rounded-lg overflow-hidden border-2 transition-all ${
                      selectedImage === img.id
                        ? "border-accent ring-2 ring-accent/20"
                        : "border-border hover:border-muted-foreground"
                    }`}
                  >
                    <Image
                      src={img.url}
                      alt="Generated variant"
                      width={400}
                      height={400}
                      className="w-full aspect-square object-cover"
                      unoptimized
                    />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Accept / Regenerate buttons */}
          {state === "selecting" && (
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setState("editing");
                  setGeneratedImages([]);
                  setSelectedImage(null);
                }}
                className="btn-secondary flex-1 text-sm"
              >
                Regenerate
              </button>
              <button
                onClick={handleAccept}
                disabled={!selectedImage}
                className="btn-primary flex-1 text-sm disabled:opacity-50"
              >
                Use Selected
              </button>
            </div>
          )}

          {/* Accepting spinner */}
          {state === "accepting" && (
            <div className="flex flex-col items-center py-4 gap-2">
              <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-muted-foreground">Saving...</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
