"use client";

import { useState, useCallback, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Bars3Icon, CheckCircleIcon } from "@heroicons/react/24/outline";
import { api, ReviewProject } from "@/lib/api";

interface CompetitionProjectsProps {
  competitionId: string;
  projects: ReviewProject[];
  isCompleted: boolean;
  onProjectsReorder: (projects: ReviewProject[]) => void;
  onFinishReview: () => void;
}

export function CompetitionProjects({
  competitionId,
  projects,
  isCompleted,
  onProjectsReorder,
  onFinishReview,
}: CompetitionProjectsProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isFinishing, setIsFinishing] = useState(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      if (isCompleted) return;

      const { active, over } = event;

      if (over && active.id !== over.id) {
        const oldIndex = projects.findIndex((p) => p.id === active.id);
        const newIndex = projects.findIndex((p) => p.id === over.id);

        const newProjects = arrayMove(projects, oldIndex, newIndex);
        onProjectsReorder(newProjects);

        if (saveTimeoutRef.current) {
          clearTimeout(saveTimeoutRef.current);
        }

        saveTimeoutRef.current = setTimeout(async () => {
          setIsSaving(true);
          setSaveError(null);
          try {
            await api.myReview.updateRankings(
              competitionId,
              newProjects.map((p) => p.id)
            );
          } catch {
            setSaveError("Failed to save rankings");
          }
          setIsSaving(false);
        }, 500);
      }
    },
    [projects, competitionId, onProjectsReorder, isCompleted]
  );

  const handleFinishReview = async () => {
    setIsFinishing(true);
    try {
      await api.myReview.updateStatus(competitionId, "completed");
      onFinishReview();
    } catch {
      setSaveError("Failed to finish review");
    }
    setIsFinishing(false);
  };

  if (projects.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-border p-8 text-center">
        <p className="text-muted-foreground text-sm">No projects in this competition.</p>
      </div>
    );
  }

  const content = (
    <div className="space-y-2">
      {projects.map((project, index) => (
        <ProjectCard
          key={project.id}
          project={project}
          competitionId={competitionId}
          rank={index + 1}
          isCompleted={isCompleted}
        />
      ))}
    </div>
  );

  return (
    <div>
      <div className="h-5 mb-4 text-xs text-muted-foreground">
        {isCompleted ? (
          <span className="text-emerald-600 flex items-center gap-1">
            <CheckCircleIcon className="w-3.5 h-3.5" />
            Review completed
          </span>
        ) : (
          <>
            {isSaving && "Saving..."}
            {saveError && <span className="text-red-500">{saveError}</span>}
            {!isSaving && !saveError && (
              <span>Drag to reorder</span>
            )}
          </>
        )}
      </div>

      {isCompleted ? (
        content
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={projects.map((p) => p.id)}
            strategy={verticalListSortingStrategy}
          >
            {content}
          </SortableContext>
        </DndContext>
      )}

      {!isCompleted && (
        <div className="mt-8 pt-6 border-t border-border">
          <button
            onClick={handleFinishReview}
            disabled={isFinishing}
            className="w-full btn-primary py-3"
          >
            {isFinishing ? "Finishing..." : "Finish Review"}
          </button>
        </div>
      )}
    </div>
  );
}

function ProjectCard({
  project,
  competitionId,
  rank,
  isCompleted,
}: {
  project: ReviewProject;
  competitionId: string;
  rank: number;
  isCompleted: boolean;
}) {
  const projectUrl = `/my-reviews/${competitionId}/${project.id}`;

  if (isCompleted) {
    return (
      <div className="flex items-center gap-3 bg-muted rounded-xl border border-border p-3.5">
        <div className="w-7 h-7 rounded-full bg-white border border-border flex items-center justify-center text-xs font-medium text-muted-foreground">
          {rank}
        </div>

        {project.main_image_url && (
          <div className="relative w-14 h-14 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
            <Image
              src={project.main_image_url}
              alt={project.title}
              fill
              className="object-cover"
              sizes="56px"
            />
          </div>
        )}

        <Link href={projectUrl} className="flex-1 text-left min-w-0">
          <h3 className="font-medium text-sm text-muted-foreground truncate">
            {project.title || "Untitled"}
          </h3>
          <p className="text-xs text-slate-400 truncate">{project.website_url}</p>
        </Link>
      </div>
    );
  }

  return (
    <SortableProjectCard
      project={project}
      competitionId={competitionId}
      rank={rank}
    />
  );
}

function SortableProjectCard({
  project,
  competitionId,
  rank,
}: {
  project: ReviewProject;
  competitionId: string;
  rank: number;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: project.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const projectUrl = `/my-reviews/${competitionId}/${project.id}`;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 bg-white rounded-xl border border-border p-3.5 hover:border-slate-300 transition-colors"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing p-1 text-slate-300 hover:text-slate-500 transition-colors"
      >
        <Bars3Icon className="w-4 h-4" />
      </button>

      <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
        {rank}
      </div>

      {project.main_image_url && (
        <div className="relative w-14 h-14 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
          <Image
            src={project.main_image_url}
            alt={project.title}
            fill
            className="object-cover"
            sizes="56px"
          />
        </div>
      )}

      <Link href={projectUrl} className="flex-1 text-left min-w-0 group">
        <h3 className="font-medium text-sm text-foreground truncate group-hover:text-accent transition-colors">
          {project.title || "Untitled"}
        </h3>
        <p className="text-xs text-muted-foreground truncate">{project.website_url}</p>
      </Link>
    </div>
  );
}
