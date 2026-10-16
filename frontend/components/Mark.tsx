export function Mark({ compact = false }: { compact?: boolean }) {
  return <div className="mark" aria-label="Noema home">
    <svg viewBox="0 0 44 44" role="img" aria-hidden="true">
      <path className="mark-shell" d="M22 3 39 13v18L22 41 5 31V13Z" />
      <path className="mark-shell" d="M13 15h18v14H13zM13 15l9 7 9-7M22 22v9" />
      <circle className="mark-core" cx="22" cy="22" r="3.5" />
    </svg>
    {!compact && <span>NOEMA</span>}
  </div>;
}
