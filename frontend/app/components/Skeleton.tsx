export function SkeletonLine({ width = "w-full", height = "h-3" }: { width?: string; height?: string }) {
  return <div className={`${width} ${height} bg-white/10 rounded animate-pulse`} />;
}

export function StatCardSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex justify-between items-center">
          <div className="space-y-1.5 flex-1">
            <SkeletonLine width="w-3/4" height="h-3" />
            <SkeletonLine width="w-1/3" height="h-2" />
          </div>
          <SkeletonLine width="w-12" height="h-4" />
        </div>
      ))}
    </div>
  );
}

export function MatchCardSkeleton() {
  return (
    <div className="space-y-2">
      <SkeletonLine width="w-1/3" height="h-2" />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <div className="w-6 h-6 rounded-full bg-white/10 animate-pulse" />
          <SkeletonLine width="w-24" height="h-3" />
        </div>
        <SkeletonLine width="w-12" height="h-5" />
        <div className="flex items-center gap-2 flex-1 justify-end">
          <SkeletonLine width="w-24" height="h-3" />
          <div className="w-6 h-6 rounded-full bg-white/10 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

export function SpotlightSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <SkeletonLine width="w-48" height="h-7" />
        <SkeletonLine width="w-16" height="h-5" />
      </div>
      <SkeletonLine width="w-32" height="h-3" />
      <div className="space-y-2 mt-4">
        <SkeletonLine width="w-full" height="h-3" />
        <SkeletonLine width="w-5/6" height="h-3" />
        <SkeletonLine width="w-4/6" height="h-3" />
        <SkeletonLine width="w-full" height="h-3" />
        <SkeletonLine width="w-3/4" height="h-3" />
      </div>
    </div>
  );
}
