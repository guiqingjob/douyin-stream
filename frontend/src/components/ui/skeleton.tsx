import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg skeleton-shimmer",
        className
      )}
      {...props}
    />
  )
}

// Creator list skeleton - matches the actual layout
function CreatorListSkeleton() {
  return (
    <div className="space-y-1 py-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-[var(--radius-card)] px-3 py-3">
          <div className="size-9 shrink-0 rounded-[var(--radius-card)] skeleton-shimmer" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-3.5 w-3/4 rounded-lg skeleton-shimmer" />
            <div className="h-2.5 w-1/2 rounded-lg skeleton-shimmer" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Asset card skeleton - matches Inbox asset card layout
function AssetCardSkeleton() {
  return (
    <div className="rounded-[var(--radius-card)] border border-border/40 bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="size-20 shrink-0 rounded-[var(--radius-card)] skeleton-shimmer" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-4 w-3/4 rounded-lg skeleton-shimmer" />
            <div className="h-3 w-1/2 rounded-lg skeleton-shimmer" />
          </div>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="h-3 w-full rounded-lg skeleton-shimmer" />
        <div className="h-3 w-2/3 rounded-lg skeleton-shimmer" />
      </div>
    </div>
  )
}

// Page header skeleton
function PageHeaderSkeleton() {
  return (
    <div className="space-y-2">
      <div className="h-7 w-48 rounded-lg skeleton-shimmer" />
      <div className="h-4 w-64 rounded-lg skeleton-shimmer" />
    </div>
  )
}

// Settings section skeleton
function SettingsSectionSkeleton() {
  return (
    <div className="rounded-[var(--radius-card)] border border-border/40 bg-card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="size-10 rounded-[var(--radius-card)] skeleton-shimmer" />
        <div className="space-y-2 flex-1">
          <div className="h-4 w-32 rounded-lg skeleton-shimmer" />
          <div className="h-3 w-48 rounded-lg skeleton-shimmer" />
        </div>
      </div>
      <div className="space-y-3 pt-2">
        <div className="h-10 w-full rounded-[var(--radius-card)] skeleton-shimmer" />
        <div className="h-10 w-full rounded-[var(--radius-card)] skeleton-shimmer" />
      </div>
    </div>
  )
}

export { Skeleton, CreatorListSkeleton, AssetCardSkeleton, PageHeaderSkeleton, SettingsSectionSkeleton }
