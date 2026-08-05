"use client";

import Link from "next/link";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
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
  PlusIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import type { ReviewProject } from "@/lib/api";
import { pickVariant } from "@/lib/utils";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";

interface RankingListProps {
  projects: ReviewProject[];
  readOnly: boolean;
  onReorder: (projects: ReviewProject[]) => void;
  onRemove?: (project: ReviewProject) => void;
}

/** The reviewer's ballot: ordered, draggable, and removable. */
export function RankingList({
  projects,
  readOnly,
  onReorder,
  onRemove,
}: RankingListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
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
      <div
        data-testid="ranked-empty"
        className="bg-white rounded-xl border border-dashed border-border p-6 text-center"
      >
        <p className="text-muted-foreground text-sm">
          {readOnly
            ? "You ranked no projects."
            : "Nothing ranked yet. Add the projects you want to back."}
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
      onRemove={onRemove ? () => onRemove(project) : undefined}
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
  onRemove?: () => void;
}

function RankingCard({
  project,
  rank,
  readOnly,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  onRemove,
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
        <div className="flex flex-col-reverse sm:flex-col items-center justify-center gap-1 flex-shrink-0">
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

        <Link
          href={`/projects/${project.slug ?? project.id}`}
          className="group flex flex-1 items-stretch gap-3 sm:gap-4 min-w-0"
        >
          <CardImage project={project} />
          <CardText project={project} readOnly={readOnly} />
        </Link>

        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            data-testid="remove-button"
            aria-label={`Remove ${project.title || "project"} from my ranking`}
            className="self-start p-2 text-slate-400 hover:text-red-600 transition-colors min-w-[44px] sm:min-w-0 min-h-[44px] sm:min-h-0 flex items-center justify-center"
          >
            <XMarkIcon className="w-5 h-5 sm:w-4 sm:h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

interface PoolListProps {
  projects: ReviewProject[];
  readOnly: boolean;
  onAdd: (project: ReviewProject) => void;
}

/** Projects the reviewer has not ranked. Order comes from the server. */
export function PoolList({ projects, readOnly, onAdd }: PoolListProps) {
  if (projects.length === 0) {
    return (
      <div
        data-testid="pool-empty"
        className="bg-white rounded-xl border border-dashed border-border p-6 text-center"
      >
        <p className="text-muted-foreground text-sm">
          Every project is in your ranking.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {projects.map((project) => (
        <div
          key={project.id}
          data-testid="pool-card"
          className="bg-white rounded-xl border border-border overflow-hidden"
        >
          <div className="flex items-stretch gap-3 sm:gap-4 p-3 sm:p-4">
            <Link
              href={`/projects/${project.slug ?? project.id}`}
              className="group flex flex-1 items-stretch gap-3 sm:gap-4 min-w-0"
            >
              <CardImage project={project} />
              <CardText project={project} readOnly={false} />
            </Link>

            {!readOnly && (
              <button
                type="button"
                onClick={() => onAdd(project)}
                data-testid="add-button"
                aria-label={`Add ${project.title || "project"} to my ranking`}
                className="self-center inline-flex items-center justify-center gap-1 flex-shrink-0 btn-secondary text-sm px-3 py-2 min-w-[44px] min-h-[44px] sm:min-h-0"
              >
                <PlusIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Rank</span>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function CardImage({ project }: { project: ReviewProject }) {
  const imageUrl =
    pickVariant(project.main_image_variants, "medium") ?? project.main_image_url;
  return (
    <div className="relative w-16 h-16 sm:w-36 sm:h-24 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
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
    <div className="flex-1 min-w-0 flex flex-col justify-center">
      <h3
        className={`font-semibold text-base sm:text-lg line-clamp-2 sm:truncate transition-colors ${
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
      <p className="hidden sm:block text-xs text-muted-foreground mt-1 truncate">
        {project.website_url}
      </p>
    </div>
  );
}
