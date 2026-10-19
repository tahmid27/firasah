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

function hourLabel(hour: number) {
  if (hour === 0) return "12am";
  if (hour === 12) return "12pm";
  return hour < 12 ? `${hour}am` : `${hour - 12}pm`;
}

// Day of week × hour of day. One hue, darker = more; the hovered cell's
// numbers show below, so nothing depends on reading the shade exactly.
export function Heatmap({ cells, unit }: { cells: HeatCell[]; unit: "gifts" }) {
  const [focus, setFocus] = useState<HeatCell | null>(null);
  const max = Math.max(1, ...cells.map((c) => c.count));
  const at = (day: number, hour: number) =>
    cells.find((c) => c.day_of_week === day && c.hour === hour);
  const busiest = cells.reduce<HeatCell | null>(
    (best, c) => (!best || c.count > best.count ? c : best),
    null,
  );

  const shown = focus ?? busiest;
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[560px] gap-0.5"
          style={{ gridTemplateColumns: "2.5rem repeat(24, minmax(0, 1fr))" }}
          onMouseLeave={() => setFocus(null)}
          role="img"
          aria-label={`Number of ${unit} by day of week and hour, UK time`}
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
                const strength = cell ? cell.count / max : 0;
                return (
                  <button
                    key={hour}
                    type="button"
                    onMouseEnter={() => cell && setFocus(cell)}
                    onFocus={() => cell && setFocus(cell)}
                    aria-label={
                      cell
                        ? `${DAY_NAMES[index]} ${hourLabel(hour)}: ${count(cell.count)} ${unit}`
                        : undefined
                    }
                    className={`h-6 rounded-[3px] outline-offset-1 ${
                      focus === cell ? "outline-2 outline-ink" : ""
                    }`}
                    style={{
                      background:
                        strength > 0
                          ? `color-mix(in oklab, var(--series-1) ${Math.round(
                              8 + strength * 92,
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
              {focus ? "" : "Busiest: "}
              <span className="font-medium text-ink">
                {DAY_NAMES[shown.day_of_week - 1]} {hourLabel(shown.hour)}–
                {hourLabel((shown.hour + 1) % 24)}
              </span>{" "}
              · {count(shown.count)} {unit}
              {shown.value !== null && ` · ${gbp(shown.value)}`}
            </>
          ) : (
            "No gifts in this period."
          )}
        </p>
        <span className="flex items-center gap-1.5 text-muted">
          Fewer
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
