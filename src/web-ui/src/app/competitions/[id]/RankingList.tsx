"use client";

import Link from "next/link";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
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
import { pickVariant } from "@/lib/utils";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";

interface RankingListProps {
  projects: ReviewProject[];
  readOnly: boolean;
  onReorder: (projects: ReviewProject[]) => void;
}

export function RankingList({
  projects,
  readOnly,
  onReorder,
}: RankingListProps) {
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
        <p className="text-muted-foreground text-sm">
          No projects in this competition.
        </p>
      </div>
    );
  }

  const cards = projects.map((project, index) => (
    <RankingCard
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
    return <div className="space-y-3">{cards}</div>;
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
        <div className="space-y-3">{cards}</div>
      </SortableContext>
    </DndContext>
  );
}

interface RankingCardProps {
  project: ReviewProject;
  rank: number;
  readOnly: boolean;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function RankingCard({
  project,
  rank,
  readOnly,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
}: RankingCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: project.id, disabled: readOnly });

  const style = readOnly
    ? undefined
    : {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      };

  const containerClass = readOnly
    ? "bg-muted rounded-xl border border-border overflow-hidden"
    : "bg-white rounded-xl border border-border hover:border-slate-300 transition-colors overflow-hidden";

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="ranked-card"
      className={containerClass}
    >
      <div className="flex items-stretch gap-3 sm:gap-4 p-3 sm:p-4">
        <div className="flex flex-col items-center justify-center gap-1 flex-shrink-0">
          {!readOnly && (
            <>
              <button
                {...attributes}
                {...listeners}
                type="button"
                aria-label={`Drag ${project.title || "project"} to reorder`}
                className="hidden sm:flex cursor-grab active:cursor-grabbing p-1 text-slate-300 hover:text-slate-500 transition-colors touch-none"
              >
                <Bars3Icon className="w-4 h-4" />
              </button>
              <div className="flex flex-col">
                <button
                  type="button"
                  onClick={onMoveUp}
                  disabled={isFirst}
                  aria-label={`Move ${project.title || "project"} up`}
                  className="p-2 sm:p-1 text-slate-400 hover:text-slate-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors min-w-[44px] sm:min-w-0 min-h-[44px] sm:min-h-0 flex items-center justify-center"
                >
                  <ChevronUpIcon className="w-5 h-5 sm:w-4 sm:h-4" />
                </button>
                <button
                  type="button"
                  onClick={onMoveDown}
                  disabled={isLast}
                  aria-label={`Move ${project.title || "project"} down`}
                  className="p-2 sm:p-1 text-slate-400 hover:text-slate-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors min-w-[44px] sm:min-w-0 min-h-[44px] sm:min-h-0 flex items-center justify-center"
                >
                  <ChevronDownIcon className="w-5 h-5 sm:w-4 sm:h-4" />
                </button>
              </div>
            </>
          )}
          <div
            data-testid="rank-badge"
            className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-base font-semibold ${
              readOnly
                ? "bg-white border border-border text-muted-foreground"
                : "bg-accent/10 text-accent"
            }`}
          >
            {rank}
          </div>
        </div>

        <CardImage project={project} />
        <CardText project={project} readOnly={readOnly} />
      </div>
    </div>
  );
}

function CardImage({ project }: { project: ReviewProject }) {
  const imageUrl =
    pickVariant(project.main_image_variants, "medium") ?? project.main_image_url;
  return (
    <div className="relative w-24 h-24 sm:w-36 sm:h-24 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl}
          alt={project.title}
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <GradientPlaceholder
          id={project.id}
          className="absolute inset-0 w-full h-full"
        />
      )}
    </div>
  );
}

function CardText({
  project,
  readOnly,
}: {
  project: ReviewProject;
  readOnly: boolean;
}) {
  return (
    <Link
      href={`/projects/${project.slug ?? project.id}`}
      className="flex-1 min-w-0 flex flex-col justify-center group"
    >
      <h3
        className={`font-semibold text-base sm:text-lg truncate transition-colors ${
          readOnly
            ? "text-muted-foreground"
            : "text-foreground group-hover:text-accent"
        }`}
      >
        {project.title || "Untitled"}
      </h3>
      {project.tagline && (
        <p
          className={`text-sm mt-0.5 line-clamp-2 ${
            readOnly ? "text-muted-foreground/80" : "text-muted-foreground"
          }`}
        >
          {project.tagline}
        </p>
      )}
      <p className="text-xs text-muted-foreground mt-1 truncate">
        {project.website_url}
      </p>
    </Link>
  );
}
