"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { applyTheme, readTheme, type Theme } from "@/lib/theme";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "system", label: "Match system", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
];

// The <html data-theme> attribute is the source of truth; components re-read
// it when the toggle changes it (in this or another copy of the toggle).
const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function ThemeToggle() {
  // The server can't know the saved choice, so it renders "system" and the
  // real choice appears after hydration.
  const theme = useSyncExternalStore(subscribe, readTheme, () => "system");

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className="flex rounded-md border border-border bg-surface-sunken p-0.5"
    >
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const selected = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            title={label}
            onClick={() => {
              applyTheme(value);
              listeners.forEach((l) => l());
            }}
            className={`grid flex-1 place-items-center rounded px-2 py-1 ${
              selected
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            <Icon size={14} aria-hidden />
            <span className="sr-only">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
