"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  PencilIcon,
  EyeIcon,
  CloudArrowUpIcon,
  TrashIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import { describeApiError } from "@/lib/api/errors";
import type { Project, ProjectImage } from "@/lib/api";
import { ProjectDetailContent } from "@/app/projects/[slug]/ProjectDetailContent";
import { EditProjectContent } from "./EditProjectContent";
import { DeleteConfirmationDialog } from "./DeleteConfirmationDialog";
import { PublishDialog } from "./PublishDialog";
import { EnterCompetitionDialog } from "./EnterCompetitionDialog";
import { useImageUpload } from "@/hooks/useImageUpload";
import type { SelectedTag } from "@/components/TagSelector";

export interface ProjectFormData {
  title: string;
  tagline: string;
  website_url: string;
  description: string;
  tag_ids: string[];
}

type ViewMode = "edit" | "preview";

interface ProjectDetailProps {
  projectId: string;
}

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const router = useRouter();
  const { isReady, isLoading: authLoading } = useRequireAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [formData, setFormData] = useState<ProjectFormData | null>(null);
  const [formInitialized, setFormInitialized] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishMissing, setPublishMissing] = useState<string[] | null>(null);
  // Set on a successful publish, cleared when the contributor enters or
  // dismisses. Publishing itself enters nothing.
  const [publishedProject, setPublishedProject] = useState<Project | null>(null);
  const [competitionError, setCompetitionError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [images, setImages] = useState<ProjectImage[]>([]);
  const [selectedTags, setSelectedTags] = useState<SelectedTag[]>([]);

  // Object literals here would change identity on every render, which is what
  // useImageUpload's uploadFile memoises on.
  const galleryTarget = useMemo(
    () => ({ kind: "project" as const, projectId }),
    [projectId],
  );
  const iconTarget = useMemo(
    () => ({ kind: "project" as const, projectId, isIcon: true }),
    [projectId],
  );

  const { uploads, uploadFiles, isUploading } = useImageUpload({
    target: galleryTarget,
    onUploadComplete: (image) => {
      setImages((prev) => [...prev, image]);
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  const {
    uploadFiles: uploadIconFiles,
  } = useImageUpload({
    target: iconTarget,
    onUploadComplete: (image) => {
      setImages((prev) => {
        const withoutOldIcon = prev.filter((img) => !img.is_icon);
        return [...withoutOldIcon, image];
      });
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  useEffect(() => {
    if (!isReady || !projectId) return;

    let cancelled = false;

    api.myProjects.get(projectId).then(
      (project) => {
        if (!cancelled) {
          setProject(project);
          setImages(project.images || []);
          if (!formInitialized) {
            setFormData({
              title: project.title,
              tagline: project.tagline,
              website_url: project.website_url,
              description: project.description,
              tag_ids: project.tags?.map((t) => t.id) || [],
            });
            setSelectedTags(
              project.tags?.map((t) => ({
                id: t.id,
                name: t.name,
                slug: t.slug,
                color: t.color,
              })) || []
            );
            setFormInitialized(true);
          }
          setIsLoading(false);
        }
      },
      (err) => {
        if (!cancelled) {
          setError(describeApiError(err, "Couldn't open this project."));
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [isReady, projectId, formInitialized]);

  // Reports whether the entry landed, because callers act on it: the
  // post-publish dialog navigates away on success and has to stay put
  // otherwise, or a refused entry would read as an accepted one.
  const handleEnterCompetition = useCallback(
    async (competitionId: string): Promise<boolean> => {
      setCompetitionError("");
      let entered = true;
      try {
        await api.myProjects.enterCompetition(projectId, competitionId);
      } catch (err) {
        entered = false;
        setCompetitionError(
          describeApiError(err, "Couldn't enter this competition.")
        );
      }

      // Always re-fetch, success or failure: a rejected entry usually means the
      // standing on screen is stale, and a stale control is worse than an
      // error. Its own try/catch, though — a failed read must not turn a write
      // that succeeded into a rejection, which is what an unguarded await here
      // did.
      try {
        setProject(await api.myProjects.get(projectId));
      } catch {
        // Keep what's on screen. The entry either happened or was reported.
      }
      return entered;
    },
    [projectId]
  );

  const handleFormChange = useCallback((data: ProjectFormData) => {
    setFormData(data);
  }, []);

  const handleTagsChange = useCallback((tags: SelectedTag[]) => {
    setSelectedTags(tags);
  }, []);

  const handleSave = async () => {
    if (!formData || !project) return;

    setIsSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      const updatedProject = await api.myProjects.update(project.id, {
        title: formData.title,
        tagline: formData.tagline,
        description: formData.description,
        website_url: formData.website_url,
        tag_ids: formData.tag_ids,
      });
      setProject(updatedProject);
      setSelectedTags(
        updatedProject.tags?.map((t) => ({
          id: t.id,
          name: t.name,
          slug: t.slug,
          color: t.color,
        })) || []
      );
      setSuccessMessage("Project saved successfully!");
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setError(describeApiError(err, "Couldn't save this project."));
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!formData || !project) return;

    setIsPublishing(true);
    setError("");
    setSuccessMessage("");

    try {
      // Persist any pending edits first so the backend validates current state.
      await api.myProjects.update(project.id, {
        title: formData.title,
        tagline: formData.tagline,
        description: formData.description,
        website_url: formData.website_url,
        tag_ids: formData.tag_ids,
      });

      const published = await api.myProjects.publish(project.id);
      const openToIt = (
        published.competition_standing?.opportunities ?? []
      ).filter((opportunity) => opportunity.eligible);
      if (openToIt.length > 0) {
        setProject(published);
        setPublishedProject(published);
        return;
      }
      // Send the owner to their project list. The public /projects/{slug} page
      // would 404 here because the project is now PENDING rather than APPROVED,
      // and the server-side fetch has no auth context to apply owner visibility.
      router.push("/my-projects");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        const missing = Array.isArray(err.body.missing)
          ? (err.body.missing as string[])
          : null;
        if (missing && missing.length > 0) {
          setPublishMissing(missing);
          setIsPublishing(false);
          return;
        }
      }
      setError(describeApiError(err, "Couldn't publish this project."));
    } finally {
      setIsPublishing(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;

    setIsDeleting(true);
    setError("");

    try {
      await api.myProjects.delete(project.id);
      router.push("/my-projects");
    } catch (err) {
      setError(describeApiError(err, "Couldn't delete this project."));
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleUpdateImageRoles = async (
    imageId: string,
    roles: { is_main?: boolean; is_hero?: boolean; is_usage?: boolean }
  ) => {
    try {
      await api.myProjects.updateImageRoles(projectId, imageId, roles);
      setImages((prev) =>
        prev.map((img) => {
          const updated = { ...img };
          // For each role being set to true, clear it from other images
          for (const [key, value] of Object.entries(roles)) {
            if (value === true && img.id !== imageId) {
              (updated as Record<string, unknown>)[key] = false;
            }
            if (img.id === imageId && value !== undefined) {
              (updated as Record<string, unknown>)[key] = value;
            }
          }
          return updated;
        })
      );
    } catch (err) {
      setError(describeApiError(err, "Couldn't update this image."));
    }
  };

  const handleDeleteIcon = async (imageId: string) => {
    try {
      await api.myProjects.deleteImage(projectId, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch (err) {
      setError(describeApiError(err, "Couldn't delete this icon."));
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    try {
      await api.myProjects.deleteImage(projectId, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch (err) {
      setError(describeApiError(err, "Couldn't delete this image."));
    }
  };

  const handleFilesSelected = (files: FileList) => {
    uploadFiles(files);
  };

  const previewProject: Project | null =
    project && formData
      ? {
          ...project,
          title: formData.title,
          tagline: formData.tagline,
          website_url: formData.website_url,
          description: formData.description,
          images: images,
          tags: selectedTags.map((t) => {
            const original = project.tags?.find((pt) => pt.id === t.id);
            return {
              id: t.id,
              name: t.name,
              slug: t.slug,
              color: t.color,
              description: original?.description ?? null,
              category_id: original?.category_id ?? null,
              category_slug: original?.category_slug ?? null,
              status: original?.status ?? "approved",
            };
          }),
        }
      : project;

  if (authLoading || isLoading) {
    return (
      <div className="py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <div className="bg-white rounded-xl border border-border p-8">
            <div className="skeleton h-6 w-1/3 mb-4" />
            <div className="skeleton h-48 w-full mb-4 rounded-lg" />
            <div className="skeleton h-4 w-2/3 mb-2" />
            <div className="skeleton h-4 w-1/2" />
          </div>
        </div>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4 inline-block">
          {error}
        </div>
        <div>
          <Link href="/my-projects" className="text-sm text-accent hover:text-accent-hover transition-colors">
            Back to my projects
          </Link>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-sm mb-4">Project not found</p>
        <Link href="/my-projects" className="text-sm text-accent hover:text-accent-hover transition-colors">
          Back to my projects
        </Link>
      </div>
    );
  }

  return (
    <>
      {/* Sticky toolbar */}
      <div className="sticky top-14 z-30 bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between py-2">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setViewMode("edit")}
              title="Edit"
              className={`p-2 rounded-lg transition-colors ${
                viewMode === "edit"
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <PencilIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("preview")}
              title="Preview"
              className={`p-2 rounded-lg transition-colors ${
                viewMode === "preview"
                  ? "bg-accent-subtle text-accent"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <EyeIcon className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            {successMessage && (
              <span className="text-emerald-600 text-sm">{successMessage}</span>
            )}
            {error && project && (
              <span className="text-red-600 text-sm">{error}</span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving || isPublishing}
              className="btn-primary text-sm py-2 px-4"
            >
              {isSaving ? (
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
              ) : (
                <span className="flex items-center gap-1.5">
                  <CloudArrowUpIcon className="w-4 h-4" />
                  Save
                </span>
              )}
            </button>
            {project.status === "draft" && (
              <button
                onClick={handlePublish}
                disabled={isPublishing || isSaving}
                className="btn-primary text-sm py-2 px-4"
              >
                {isPublishing ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  "Publish"
                )}
              </button>
            )}
            <button
              onClick={() => setShowDeleteDialog(true)}
              title="Delete"
              className="p-2 rounded-lg text-muted-foreground border border-border hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content: edit or preview mode */}
      {viewMode === "edit" && formData ? (
        <EditProjectContent
          project={project}
          formData={formData}
          onChange={handleFormChange}
          onTagsChange={handleTagsChange}
          images={images}
          uploads={uploads}
          isUploading={isUploading}
          onFilesSelected={handleFilesSelected}
          onUpdateImageRoles={handleUpdateImageRoles}
          onDeleteImage={handleDeleteImage}
          iconImage={images.find((img) => img.is_icon) ?? null}
          onIconFilesSelected={(files) => uploadIconFiles(files)}
          onDeleteIcon={handleDeleteIcon}
          competitionStanding={project.competition_standing ?? null}
          competitionError={competitionError}
          onEnterCompetition={async (competitionId) => {
            await handleEnterCompetition(competitionId);
          }}
        />
      ) : (
        previewProject && (
          <ProjectDetailContent
            project={previewProject}
            projectId={projectId}
          />
        )
      )}

      <div className="py-6 text-center">
        <Link href="/my-projects" className="text-sm text-accent hover:text-accent-hover transition-colors">
          Back to my projects
        </Link>
      </div>

      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        projectTitle={project.title || "Untitled Project"}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteDialog(false)}
        isDeleting={isDeleting}
      />

      <PublishDialog
        isOpen={publishMissing !== null}
        missing={publishMissing ?? []}
        onClose={() => setPublishMissing(null)}
      />

      {publishedProject && (
        <EnterCompetitionDialog
          opportunities={(
            publishedProject.competition_standing?.opportunities ?? []
          ).filter((opportunity) => opportunity.eligible)}
          error={competitionError}
          onEnter={async (competitionId) => {
            // Only leave on success. Navigating regardless sent the
            // contributor to their project list believing they had entered,
            // with the reason they hadn't rendered on the page behind them.
            if (!(await handleEnterCompetition(competitionId))) return;
            setPublishedProject(null);
            router.push("/my-projects");
          }}
          onDismiss={() => {
            setPublishedProject(null);
            router.push("/my-projects");
          }}
        />
      )}
    </>
  );
}
