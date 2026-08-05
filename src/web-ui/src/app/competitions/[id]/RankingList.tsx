"use client";

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
import { ProjectTile } from "@/components/ProjectTile";

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

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="ranked-card"
      className="flex items-start gap-3"
    >
      <div className={TILE_WIDTH_CLASS}>
        <ProjectCardTile project={project} dimmed={readOnly} />
      </div>

      <ControlColumn>
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
            <button
              type="button"
              onClick={onMoveUp}
              disabled={isFirst}
              aria-label={`Move ${project.title || "project"} up`}
              className={CONTROL_BUTTON_CLASS}
            >
              <ChevronUpIcon className="w-5 h-5 sm:w-4 sm:h-4" />
            </button>
            <button
              type="button"
              onClick={onMoveDown}
              disabled={isLast}
              aria-label={`Move ${project.title || "project"} down`}
              className={CONTROL_BUTTON_CLASS}
            >
              <ChevronDownIcon className="w-5 h-5 sm:w-4 sm:h-4" />
            </button>
          </>
        )}

        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            data-testid="remove-button"
            aria-label={`Remove ${project.title || "project"} from my ranking`}
            className={`${CONTROL_BUTTON_CLASS} hover:text-red-600`}
          >
            <XMarkIcon className="w-5 h-5 sm:w-4 sm:h-4" />
          </button>
        )}
      </ControlColumn>
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
          className="flex items-start gap-3"
        >
          <div className={TILE_WIDTH_CLASS}>
            <ProjectCardTile project={project} dimmed={false} />
          </div>

          {!readOnly && (
            <ControlColumn>
              <button
                type="button"
                onClick={() => onAdd(project)}
                data-testid="add-button"
                aria-label={`Add ${project.title || "project"} to my ranking`}
                className="inline-flex items-center justify-center gap-1 btn-secondary text-sm px-3 py-2 min-w-[44px] min-h-[44px] sm:min-h-0"
              >
                <PlusIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Rank</span>
              </button>
            </ControlColumn>
          )}
        </div>
      ))}
    </div>
  );
}

// Capped at the listing card's 240px rather than filling the panel. A 4:3 image
// stretched to full panel width makes each entry ~300px tall, which turns a
// twelve-project ballot into a very long scroll. Leaves whitespace to the right
// on wide panels; that is the intended trade.
const TILE_WIDTH_CLASS = "w-full max-w-[240px] min-w-0";

const CONTROL_BUTTON_CLASS =
  "p-2 sm:p-1 text-slate-400 hover:text-slate-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors min-w-[44px] sm:min-w-0 min-h-[44px] sm:min-h-0 flex items-center justify-center";

/** Ballot controls, stacked beside the card rather than nested inside its link. */
function ControlColumn({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-1 flex-shrink-0 pt-1">
      {children}
    </div>
  );
}

/** A ballot project rendered with the same tile the listing page uses. */
function ProjectCardTile({
  project,
  dimmed,
}: {
  project: ReviewProject;
  dimmed: boolean;
}) {
  return (
    <ProjectTile
      id={project.id}
      href={`/projects/${project.slug ?? project.id}`}
      imageUrl={project.in_use_image_url || project.hero_banner_url || null}
      title={project.title || "Untitled"}
      tagline={project.tagline}
      categoryName={project.category_name}
      dimmed={dimmed}
    />
  );
}
