// Temporary: marks where each chosen visual will go until its page is built.
export function PlannedVisuals({
  items,
}: {
  items: [id: string, title: string][];
}) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map(([id, title]) => (
        <li
          key={id}
          className="flex min-h-32 flex-col justify-between rounded-lg border border-dashed border-border bg-surface p-4"
        >
          <span className="text-xs font-medium text-muted">{id}</span>
          <span className="text-sm text-ink-2">{title}</span>
        </li>
      ))}
    </ul>
  );
}
