"use client";

import { useState } from "react";

import { count, gbp } from "@/lib/format";

export type HeatCell = {
  day_of_week: number; // 1 = Monday
  hour: number;
  count: number;
  value: number | null;
};

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// minCount: an average over fewer posts than this is too noisy to shade or
// call the top slot; those cells are drawn hollow instead.
type Measure = {
  label: string;
  of: (c: HeatCell) => number;
  minCount?: number;
};

// What a cell means depends on the chart: donations (count and money) or
// posts (count and the average engagement of posts made in that slot).
const KINDS = {
  donations: {
    measures: [
      { label: "Individual donations", of: (c: HeatCell) => c.count },
      { label: "Money raised", of: (c: HeatCell) => c.value ?? 0 },
    ] as Measure[],
    describe: (c: HeatCell) =>
      `${count(c.count)} donation${c.count === 1 ? "" : "s"} · ${gbp(c.value ?? 0)}`,
    empty: "No donations in this period.",
  },
  posts: {
    measures: [
      {
        label: "Average engagement",
        of: (c: HeatCell) => c.value ?? 0,
        minCount: 3,
      },
      { label: "Number of posts", of: (c: HeatCell) => c.count },
    ] as Measure[],
    describe: (c: HeatCell) =>
      `${count(c.count)} post${c.count === 1 ? "" : "s"}${
        c.value === null
          ? ""
          : ` · ${(c.value * 100).toFixed(1)}% average engagement`
      }`,
    empty: "No posts in this period.",
  },
};

function hourLabel(hour: number) {
  if (hour === 0) return "12am";
  if (hour === 12) return "12pm";
  return hour < 12 ? `${hour}am` : `${hour - 12}pm`;
}

// Day of week × hour of day with a switch between two measures. One hue,
// darker = more; the hovered (or top) slot's numbers show below, so nothing
// depends on reading the shade exactly.
export function Heatmap({
  cells,
  kind,
}: {
  cells: HeatCell[];
  kind: keyof typeof KINDS;
}) {
  const { measures, describe, empty } = KINDS[kind];
  const [index, setIndex] = useState(0);
  const [focus, setFocus] = useState<HeatCell | null>(null);
  const measure = measures[index];
  const of = measure.of;
  const enough = (c: HeatCell) => c.count >= (measure.minCount ?? 1);
  const counted = cells.filter(enough);
  // Shade from the lowest to the highest counted slot, so differences show
  const low = measure.minCount ? Math.min(...counted.map(of)) : 0;
  const high = Math.max(...counted.map(of), low + 1e-9);
  const strengthOf = (c: HeatCell) =>
    enough(c) ? 0.08 + 0.92 * ((of(c) - low) / (high - low || 1)) : 0;
  const at = (day: number, hour: number) =>
    cells.find((c) => c.day_of_week === day && c.hour === hour);
  const busiest = counted.reduce<HeatCell | null>(
    (best, c) => (!best || of(c) > of(best) ? c : best),
    null,
  );
  const thin = cells.some((c) => c.count > 0 && !enough(c));
  const shown = focus ?? (busiest && of(busiest) > 0 ? busiest : null);

  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="Show"
        className="flex w-fit rounded-md border border-border bg-surface-sunken p-0.5 text-xs"
      >
        {measures.map((m, i) => (
          <button
            key={m.label}
            type="button"
            role="radio"
            aria-checked={index === i}
            onClick={() => setIndex(i)}
            className={`rounded px-2.5 py-1 ${
              index === i
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[560px] gap-0.5"
          style={{ gridTemplateColumns: "2.5rem repeat(24, minmax(0, 1fr))" }}
          onMouseLeave={() => setFocus(null)}
          role="img"
          aria-label={`${measure.label} by day of week and hour, UK time`}
        >
          <span />
          {Array.from({ length: 24 }, (_, hour) => (
            <span key={hour} className="text-center text-[10px] text-muted">
              {hour % 3 === 0 ? hourLabel(hour) : ""}
            </span>
          ))}
          {DAYS.map((day, index) => (
            <Row key={day} label={day}>
              {Array.from({ length: 24 }, (_, hour) => {
                const cell = at(index + 1, hour);
                const strength = cell ? strengthOf(cell) : 0;
                const hollow = !!cell && cell.count > 0 && !enough(cell);
                return (
                  <button
                    key={hour}
                    type="button"
                    onMouseEnter={() => cell && setFocus(cell)}
                    onFocus={() => cell && setFocus(cell)}
                    aria-label={
                      cell
                        ? `${DAY_NAMES[index]} ${hourLabel(hour)}: ${describe(cell)}`
                        : undefined
                    }
                    className={`h-6 rounded-[3px] outline-offset-1 ${
                      focus === cell ? "outline-2 outline-ink" : ""
                    } ${hollow ? "border border-dashed border-muted" : ""}`}
                    style={{
                      background:
                        strength > 0
                          ? `color-mix(in oklab, var(--series-1) ${Math.round(
                              strength * 100,
                            )}%, var(--surface-sunken))`
                          : "var(--surface-sunken)",
                    }}
                  />
                );
              })}
            </Row>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-2">
        <p className="tabular-nums">
          {shown ? (
            <>
              {focus
                ? ""
                : measure.minCount
                  ? `Top (${measure.minCount}+ posts): `
                  : "Top: "}
              <span className="font-medium text-ink">
                {DAY_NAMES[shown.day_of_week - 1]} {hourLabel(shown.hour)}–
                {hourLabel((shown.hour + 1) % 24)}
              </span>{" "}
              · {describe(shown)}
            </>
          ) : (
            empty
          )}
        </p>
        {thin && measure.minCount && (
          <span className="flex items-center gap-1.5 text-muted">
            <span
              aria-hidden
              className="size-3 rounded-[3px] border border-dashed border-muted"
            />
            Fewer than {measure.minCount} posts
          </span>
        )}
        <span className="flex items-center gap-1.5 text-muted">
          Less
          <span
            aria-hidden
            className="h-2 w-16 rounded-sm"
            style={{
              background:
                "linear-gradient(to right, color-mix(in oklab, var(--series-1) 8%, var(--surface-sunken)), var(--series-1))",
            }}
          />
          More
        </span>
      </div>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <span className="self-center pr-1 text-xs text-muted">{label}</span>
      {children}
    </>
  );
}
