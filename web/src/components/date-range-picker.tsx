"use client";

import { Calendar, Check, ChevronDown } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { PRESETS, withRange, type DateRange } from "@/lib/date-range";

export function DateRangePicker({
  range,
  today,
}: {
  range: DateRange;
  today: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const [from, setFrom] = useState(range.start);
  const [to, setTo] = useState(range.end);
  const [pending, startTransition] = useTransition();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function go(next: { preset: string; from?: string; to?: string }) {
    setOpen(false);
    startTransition(() =>
      router.push(`${pathname}${withRange(searchParams, next)}`),
    );
  }

  const presetLabel =
    PRESETS.find((p) => p.key === range.preset)?.label ?? "Custom range";
  const customValid = !!from && !!to && from <= to;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="dialog"
        className={`flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm shadow-xs hover:bg-surface-sunken ${
          pending ? "opacity-60" : ""
        }`}
      >
        <Calendar size={16} className="text-muted" aria-hidden />
        <span className="font-medium">{presetLabel}</span>
        <span className="hidden text-muted sm:inline">{range.label}</span>
        <ChevronDown size={16} className="text-muted" aria-hidden />
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Choose date range"
          className="absolute right-0 z-10 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-surface p-1 shadow-lg"
        >
          <ul>
            {PRESETS.map((p) => {
              const selected = p.key === range.preset;
              return (
                <li key={p.key}>
                  <button
                    type="button"
                    onClick={() => go({ preset: p.key })}
                    aria-pressed={selected}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-surface-sunken"
                  >
                    <span className="grid w-4 place-items-center">
                      {selected && (
                        <Check size={16} strokeWidth={3} aria-hidden />
                      )}
                    </span>
                    {p.label}
                  </button>
                </li>
              );
            })}
          </ul>
          <form
            className="mt-1 border-t border-hairline p-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (customValid) go({ preset: "custom", from, to });
            }}
          >
            <p className="mb-2 flex items-center gap-2 text-xs font-medium text-ink-2">
              <span className="grid w-4 place-items-center">
                {range.preset === "custom" && (
                  <Check size={16} strokeWidth={3} aria-hidden />
                )}
              </span>
              Custom range
            </p>
            <div className="flex items-center gap-2">
              <label className="min-w-0 flex-1 text-xs text-muted">
                From
                <input
                  type="date"
                  value={from}
                  max={to || today}
                  onChange={(e) => setFrom(e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-ink"
                />
              </label>
              <label className="min-w-0 flex-1 text-xs text-muted">
                To
                <input
                  type="date"
                  value={to}
                  min={from}
                  max={today}
                  onChange={(e) => setTo(e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-ink"
                />
              </label>
            </div>
            <button
              type="submit"
              disabled={!customValid}
              className="mt-2 w-full rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-ink disabled:opacity-50"
            >
              Apply
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
