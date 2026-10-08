// Shimmer placeholders shaped like the page that's loading.

export function Skeleton({ className = "", style }) {
  return <div className={`skeleton ${className}`.trim()} style={style} aria-hidden="true" />;
}

const Lines = ({ widths }) => widths.map((w, i) => <Skeleton key={i} className="skeleton-line" style={{ width: w }} />);

export function PageSkeleton({ kind = "page" }) {
  return (
    <div className="page-skeleton" role="status" aria-label="Loading">
      <Skeleton className="skeleton-title" />
      {kind === "calendar" && (
        <>
          <Skeleton className="skeleton-line" style={{ width: 280, height: 36 }} />
          <div className="skeleton-calendar">
            {Array.from({ length: 35 }, (_, i) => (
              <Skeleton key={i} className="skeleton-cell" />
            ))}
          </div>
        </>
      )}
      {kind === "rows" &&
        Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton-row">
            <Skeleton className="skeleton-photo" />
            <Skeleton className="skeleton-photo" />
            <Skeleton className="skeleton-photo" />
            <div className="skeleton-lines">
              <Lines widths={["70%", "50%"]} />
            </div>
          </div>
        ))}
      {kind === "hero" && (
        <div className="sunset-hero">
          <Skeleton className="skeleton-photo" />
          <div className="sunset-hero-side skeleton-lines">
            <Lines widths={["40%", "60%", "90%", "90%", "90%", "90%"]} />
          </div>
        </div>
      )}
      {kind === "chart" && <Skeleton style={{ height: 420 }} />}
      {kind === "page" && (
        <>
          <Lines widths={["60%", "45%"]} />
          <Skeleton style={{ height: 320, marginTop: 16 }} />
        </>
      )}
    </div>
  );
}
