export function Mark({ compact = false }: { compact?: boolean }) {
  return <div className="mark" aria-label="Noema home">
    <svg viewBox="0 0 44 44" role="img" aria-hidden="true">
      <path d="M7 29 17 8l20 7-10 21Z" />
      <circle cx="17" cy="8" r="3" /><circle cx="37" cy="15" r="3" />
      <circle cx="27" cy="36" r="3" /><circle cx="7" cy="29" r="3" />
      <path d="m17 8 10 28M7 29l30-14" />
    </svg>
    {!compact && <span>NOEMA</span>}
  </div>;
}
