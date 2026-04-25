export function CreatorSkeleton() {
  return (
    <section className="w-full grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="rounded-[var(--radius-card)] border border-border/60 bg-card p-5 apple-shadow-md">
          <div className="flex items-start gap-4">
            <div className="size-10 shrink-0 rounded-[var(--radius-card)] skeleton-shimmer" />
            <div className="min-w-0 flex-1 space-y-3">
              <div className="h-4 w-2/3 rounded-md skeleton-shimmer" />
              <div className="grid grid-cols-3 gap-2">
                <div className="h-10 rounded-md skeleton-shimmer" />
                <div className="h-10 rounded-md skeleton-shimmer" />
                <div className="h-10 rounded-md skeleton-shimmer" />
              </div>
            </div>
          </div>
          <div className="mt-6 space-y-3">
            <div className="h-3 w-full rounded-md skeleton-shimmer" />
            <div className="grid grid-cols-2 gap-3">
              <div className="h-8 rounded-md skeleton-shimmer" />
              <div className="h-8 rounded-md skeleton-shimmer" />
            </div>
            <div className="h-3 w-1/2 rounded-md skeleton-shimmer" />
          </div>
        </div>
      ))}
    </section>
  );
}
