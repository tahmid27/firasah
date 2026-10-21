"use client";

import { useSyncExternalStore } from "react";

import { applyDensity, readDensity, type Density } from "@/lib/density";

const OPTIONS: { value: Density; label: string }[] = [
  { value: "compact", label: "Compact" },
  { value: "normal", label: "Normal" },
  { value: "spacious", label: "Spacious" },
];

const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function DensityToggle() {
  // The server can't know the saved choice, so it renders "normal" and the
  // real choice appears after hydration.
  const density = useSyncExternalStore(subscribe, readDensity, () => "normal");

  return (
    <div
      role="radiogroup"
      aria-label="Layout density"
      className="flex rounded-md border border-border bg-surface-sunken p-0.5"
    >
      {OPTIONS.map(({ value, label }) => {
        const selected = density === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => {
              applyDensity(value);
              listeners.forEach((l) => l());
            }}
            className={`flex-1 rounded px-1.5 py-1 text-xs ${
              selected
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
