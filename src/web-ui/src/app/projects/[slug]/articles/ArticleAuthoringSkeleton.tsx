// The authoring surface loads in two hops — the project, then the article —
// and both show this, so the second wait is not a layout shift.
//
// Deliberately the same boxes, in the same places, at the same heights as
// ArticleAuthoringPage — the earlier skeleton was a plain white card, so the
// handover moved every control on the page and read as a second page load.
// Its editor slot is the same `h-[60vh]` block next/dynamic falls back to, so
// the editor's own arrival does not move anything either.
export function ArticleAuthoringSkeleton() {
  return (
    <>
      <div className="sticky top-14 z-30 bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between py-2">
          <div className="skeleton h-5 w-48" />
          <div className="flex items-center gap-2">
            <div className="skeleton h-9 w-24 rounded-lg" />
            <div className="skeleton h-9 w-20 rounded-lg" />
            <div className="skeleton h-9 w-9 rounded-lg" />
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 sm:items-center">
          <div className="skeleton h-[50px] w-full rounded-lg" />
          <div className="skeleton h-[50px] w-40 rounded-lg" />
        </div>
        <div className="flex gap-1">
          <div className="skeleton h-[38px] w-20" />
          <div className="skeleton h-[38px] w-32" />
        </div>
        <div className="skeleton h-[60vh] w-full" />
      </div>
    </>
  );
}
