"use client";

import Image from "next/image";
import Link from "next/link";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
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
import {
  Bars3Icon,
  ChevronUpIcon,
  ChevronDownIcon,
} from "@heroicons/react/24/outline";
import type { ReviewProject } from "@/lib/api";

interface RankingListProps {
  projects: ReviewProject[];
  readOnly: boolean;
  onReorder: (projects: ReviewProject[]) => void;
}

export function RankingList({ projects, readOnly, onReorder }: RankingListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    if (readOnly) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = projects.findIndex((p) => p.id === active.id);
    const newIndex = projects.findIndex((p) => p.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    onReorder(arrayMove(projects, oldIndex, newIndex));
  };

  const moveBy = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= projects.length) return;
    onReorder(arrayMove(projects, index, target));
  };

  if (projects.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-border p-6 text-center">
        <p className="text-muted-foreground text-sm">No projects in this competition.</p>
      </div>
    );
  }

  const rows = projects.map((project, index) => (
    <Row
      key={project.id}
      project={project}
      rank={index + 1}
      readOnly={readOnly}
      isFirst={index === 0}
      isLast={index === projects.length - 1}
      onMoveUp={() => moveBy(index, -1)}
      onMoveDown={() => moveBy(index, 1)}
    />
  ));

  if (readOnly) {
    return <div className="space-y-2">{rows}</div>;
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={projects.map((p) => p.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="space-y-2">{rows}</div>
      </SortableContext>
    </DndContext>
  );
}

interface RowProps {
  project: ReviewProject;
  rank: number;
  readOnly: boolean;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function Row(props: RowProps) {
  if (props.readOnly) {
    return <ReadOnlyRow project={props.project} rank={props.rank} />;
  }
  return <SortableRow {...props} />;
}

function ReadOnlyRow({ project, rank }: { project: ReviewProject; rank: number }) {
  return (
    <div className="flex items-center gap-3 bg-muted rounded-xl border border-border p-3.5">
      <div className="w-7 h-7 rounded-full bg-white border border-border flex items-center justify-center text-xs font-medium text-muted-foreground">
        {rank}
      </div>
      <ProjectThumb project={project} />
      <ProjectLink project={project} muted />
    </div>
  );
}

function SortableRow({
  project,
  rank,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
}: RowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: project.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 sm:gap-3 bg-white rounded-xl border border-border p-2.5 sm:p-3.5 hover:border-slate-300 transition-colors"
    >
      {/* Drag handle (works on desktop + as fallback) */}
      <button
        {...attributes}
        {...listeners}
        type="button"
        aria-label={`Drag ${project.title || "project"} to reorder`}
        className="hidden sm:flex cursor-grab active:cursor-grabbing p-1 text-slate-300 hover:text-slate-500 transition-colors touch-none"
      >
        <Bars3Icon className="w-4 h-4" />
      </button>

      {/* Up/Down buttons (primary path on mobile, accessible everywhere) */}
      <div className="flex flex-col">
        <button
          type="button"
          onClick={onMoveUp}
          disabled={isFirst}
          aria-label={`Move ${project.title || "project"} up`}
          className="p-1 text-slate-400 hover:text-slate-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronUpIcon className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={onMoveDown}
          disabled={isLast}
          aria-label={`Move ${project.title || "project"} down`}
          className="p-1 text-slate-400 hover:text-slate-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronDownIcon className="w-4 h-4" />
        </button>
      </div>

      <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground flex-shrink-0">
        {rank}
      </div>

      <ProjectThumb project={project} />
      <ProjectLink project={project} />
    </div>
  );
}

function ProjectThumb({ project }: { project: ReviewProject }) {
  if (!project.main_image_url) return null;
  return (
    <div className="relative w-12 h-12 sm:w-14 sm:h-14 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
      <Image
        src={project.main_image_url}
        alt={project.title}
        fill
        className="object-cover"
        sizes="56px"
      />
    </div>
  );
}

function ProjectLink({
  project,
  muted = false,
}: {
  project: ReviewProject;
  muted?: boolean;
}) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="flex-1 text-left min-w-0 group"
    >
      <h3
        className={`font-medium text-sm truncate transition-colors ${
          muted
            ? "text-muted-foreground"
            : "text-foreground group-hover:text-accent"
        }`}
      >
        {project.title || "Untitled"}
      </h3>
      <p className="text-xs text-muted-foreground truncate">
        {project.website_url}
      </p>
    </Link>
  );
}
