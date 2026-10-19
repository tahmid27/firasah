import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { percent } from "@/lib/format";

// A change shown with an arrow and words as well as colour, so it never
// relies on colour alone.
export function Delta({ pct, label }: { pct: number | null; label: string }) {
  if (pct === null) {
    return <p className="text-xs text-muted">No comparison yet · {label}</p>;
  }
  const up = pct > 0;
  const flat = pct === 0;
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  return (
    <p className="flex flex-wrap items-center gap-x-1 text-xs text-muted">
      <span
        className={`inline-flex items-center font-medium ${
          flat ? "text-ink-2" : up ? "text-delta-up" : "text-delta-down"
        }`}
      >
        <Icon size={14} aria-hidden />
        <span className="sr-only">
          {flat ? "No change" : up ? "Up" : "Down"}
        </span>
        {percent(pct)}
      </span>
      {label}
    </p>
  );
}
