export function SkeletonScreen() {
  return (
    <div className="h-full w-full bg-base p-6 overflow-y-auto">
      <div className="skeleton h-8 w-48 rounded-lg mb-6" />
      <div className="grid grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton rounded-xl h-[116px]" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3 mt-5">
        <div className="col-span-2 skeleton rounded-xl h-[280px]" />
        <div className="skeleton rounded-xl h-[280px]" />
      </div>
    </div>
  );
}
