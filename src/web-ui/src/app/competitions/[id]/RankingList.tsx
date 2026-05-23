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
  type DragEndEvent,
  type DraggableAttributes,
  type DraggableSyntheticListeners,
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
import type { RankingVariant } from "./useVariantPref";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";

interface RankingListProps {
  projects: ReviewProject[];
  readOnly: boolean;
  variant: RankingVariant;
  onReorder: (projects: ReviewProject[]) => void;
}

export function RankingList({
  projects,
  readOnly,
  variant,
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
      variant={variant}
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
  variant: RankingVariant;
  readOnly: boolean;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function RankingCard(props: RankingCardProps) {
  if (props.readOnly) {
    return <ReadOnlyCard {...props} />;
  }
  return <SortableCard {...props} />;
}

function SortableCard(props: RankingCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.project.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="ranked-card"
      className="bg-white rounded-xl border border-border hover:border-slate-300 transition-colors overflow-hidden"
    >
      <CardBody
        {...props}
        dragHandleProps={{ attributes, listeners }}
      />
    </div>
  );
}

function ReadOnlyCard(props: RankingCardProps) {
  return (
    <div data-testid="ranked-card" className="bg-muted rounded-xl border border-border overflow-hidden">
      <CardBody {...props} dragHandleProps={null} muted />
    </div>
  );
}

interface CardBodyProps extends RankingCardProps {
  dragHandleProps:
    | { attributes: DraggableAttributes; listeners: DraggableSyntheticListeners }
    | null;
  muted?: boolean;
}

function CardBody(props: CardBodyProps) {
  return <LayoutLeft {...props} />;
}

function LayoutLeft({
  project,
  rank,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  dragHandleProps,
  muted = false,
}: CardBodyProps) {
  const interactive = dragHandleProps !== null;
  return (
    <div className="flex items-stretch gap-3 sm:gap-4 p-3 sm:p-4">
      {/* Controls column (left) */}
      <div className="flex flex-col items-center justify-center gap-1 flex-shrink-0">
        {interactive && (
          <button
            {...dragHandleProps.attributes}
            {...dragHandleProps.listeners}
            type="button"
            aria-label={`Drag ${project.title || "project"} to reorder`}
            className="hidden sm:flex cursor-grab active:cursor-grabbing p-1 text-slate-300 hover:text-slate-500 transition-colors touch-none"
          >
            <Bars3Icon className="w-4 h-4" />
          </button>
        )}
        {interactive && (
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
        )}
        <div
          data-testid="rank-badge"
          data-variant="L"
          className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-base font-semibold ${
            muted
              ? "bg-white border border-border text-muted-foreground"
              : "bg-accent/10 text-accent"
          }`}
        >
          {rank}
        </div>
      </div>

      {/* Image */}
      <CardImage project={project} />

      {/* Text block (links to project) */}
      <CardText project={project} muted={muted} />
    </div>
  );
}


function CardImage({ project }: { project: ReviewProject }) {
  const imageUrl =
    pickVariant(project.main_image_variants, "medium") ?? project.main_image_url;
  return (
    <div className="relative w-24 h-24 sm:w-36 sm:h-24 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
      {imageUrl ? (
        <Image
          src={imageUrl}
          alt={project.title}
          fill
          className="object-cover"
          sizes="(min-width: 640px) 144px, 96px"
        />
      ) : (
        <GradientPlaceholder id={project.id} className="absolute inset-0 w-full h-full" />
      )}
    </div>
  );
}

function CardText({
  project,
  muted = false,
}: {
  project: ReviewProject;
  muted?: boolean;
}) {
  return (
    <Link
      href={`/projects/${project.slug ?? project.id}`}
      className="flex-1 min-w-0 flex flex-col justify-center group"
    >
      <h3
        className={`font-semibold text-base sm:text-lg truncate transition-colors ${
          muted
            ? "text-muted-foreground"
            : "text-foreground group-hover:text-accent"
        }`}
      >
        {project.title || "Untitled"}
      </h3>
      {project.tagline && (
        <p
          className={`text-sm mt-0.5 line-clamp-2 ${
            muted ? "text-muted-foreground/80" : "text-muted-foreground"
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
