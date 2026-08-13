// The authoring surface loads in two hops — the project, then the article —
// and both show this. One component so the second wait is not a layout shift.
export function ArticleAuthoringSkeleton() {
  return (
    <div className="py-8 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto bg-white rounded-xl border border-border p-8">
        <div className="skeleton h-6 w-1/3 mb-4" />
        <div className="skeleton h-48 w-full mb-4 rounded-lg" />
        <div className="skeleton h-4 w-2/3 mb-2" />
      </div>
    </div>
  );
}
