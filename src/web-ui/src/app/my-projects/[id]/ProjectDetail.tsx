"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PencilIcon, EyeIcon, CloudArrowUpIcon, TrashIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import { api } from "@/lib/api";
import type { Project, ProjectImage } from "@/lib/api";
import { ReadOnlyProjectDetail } from "./ReadOnlyProjectDetail";
import { EditProjectDetail, type ProjectFormData } from "./EditProjectDetail";
import { DeleteConfirmationDialog } from "./DeleteConfirmationDialog";
import { useImageUpload } from "@/hooks/useImageUpload";
import type { SelectedTag } from "@/components/TagSelector";

type ViewMode = "edit" | "preview";

interface ProjectDetailProps {
  projectId: string;
}

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [formData, setFormData] = useState<ProjectFormData | null>(null);
  const [formInitialized, setFormInitialized] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [images, setImages] = useState<ProjectImage[]>([]);
  const [selectedTags, setSelectedTags] = useState<SelectedTag[]>([]);

  const { uploads, uploadFiles, isUploading } = useImageUpload({
    projectId,
    onUploadComplete: (image) => {
      setImages((prev) => [...prev, image]);
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
      return;
    }

    if (!isAuthenticated || !projectId) {
      return;
    }

    let cancelled = false;

    api.myProjects.get(projectId).then(
      (project) => {
        if (!cancelled) {
          setProject(project);
          setImages(project.images || []);
          if (!formInitialized) {
            setFormData({
              title: project.title,
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
          setError(err instanceof Error ? err.message : "Failed to load project");
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated, projectId, router, formInitialized]);

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
      setError(err instanceof Error ? err.message : "Failed to save project");
    } finally {
      setIsSaving(false);
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
      setError(err instanceof Error ? err.message : "Failed to delete project");
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleSetMainImage = async (imageId: string) => {
    try {
      const updatedImage = await api.myProjects.setMainImage(projectId, imageId);
      setImages((prev) =>
        prev.map((img) => ({
          ...img,
          is_main: img.id === updatedImage.id,
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set main image");
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    try {
      await api.myProjects.deleteImage(projectId, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete image");
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
      <div className="bg-white rounded-xl border border-border p-8">
        <div className="skeleton h-6 w-1/3 mb-4" />
        <div className="skeleton h-48 w-full mb-4 rounded-lg" />
        <div className="skeleton h-4 w-2/3 mb-2" />
        <div className="skeleton h-4 w-1/2" />
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
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-lg text-sm mb-4">
          {successMessage}
        </div>
      )}

      <div className="bg-white rounded-xl border border-border">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
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
            <button
              onClick={handleSave}
              disabled={isSaving}
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
            <button
              onClick={() => setShowDeleteDialog(true)}
              title="Delete"
              className="p-2 rounded-lg text-muted-foreground border border-border hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-5">
          {viewMode === "edit" && formData ? (
            <EditProjectDetail
              project={project}
              formData={formData}
              onChange={handleFormChange}
              onTagsChange={handleTagsChange}
              images={images}
              uploads={uploads}
              isUploading={isUploading}
              onFilesSelected={handleFilesSelected}
              onSetMainImage={handleSetMainImage}
              onDeleteImage={handleDeleteImage}
            />
          ) : (
            previewProject && <ReadOnlyProjectDetail project={previewProject} />
          )}
        </div>
      </div>

      <div className="mt-6 text-center">
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
    </>
  );
}
