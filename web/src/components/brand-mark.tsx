// Two nodes and a gold peak. Colour follows the text colour (navy in light
// mode, ice blue in dark); the peak always uses the second chart colour.
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden className={className}>
      <g stroke="currentColor" strokeWidth="4.2" fill="none">
        <line x1="20" y1="44" x2="34" y2="24" />
        <line x1="34" y1="24" x2="46" y2="38" />
      </g>
      <circle cx="20" cy="44" r="6.5" fill="currentColor" />
      <circle cx="46" cy="38" r="6.5" fill="currentColor" />
      <circle cx="34" cy="24" r="6.5" style={{ fill: "var(--series-2)" }} />
    </svg>
  );
}
