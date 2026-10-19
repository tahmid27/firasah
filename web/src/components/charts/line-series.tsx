"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { count, dayMonth, monthShort, monthYear } from "@/lib/format";

import type { Series } from "./stacked-bars";

type Row = { period: string } & Record<string, number | string | null>;

const compact = new Intl.NumberFormat("en-GB", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function periodTick(interval: "day" | "week" | "month") {
  return (p: string) => (interval === "month" ? monthShort(p) : dayMonth(p));
}

export function periodTitle(interval: "day" | "week" | "month") {
  return (p: string) =>
    interval === "month"
      ? monthYear(p)
      : interval === "week"
        ? `Week of ${dayMonth(p)} ${p.slice(0, 4)}`
        : `${dayMonth(p)} ${p.slice(0, 4)}`;
}

export function Legend({ series }: { series: Series[] }) {
  if (series.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {series.map((s) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="h-0.5 w-3 rounded-full"
            style={{ background: s.colour }}
          />
          {s.label}
        </li>
      ))}
    </ul>
  );
}

// Counts over time, one line per series. A gap in the data stays a gap (no
// reading isn't zero). The y-axis fits the data, so slow growth is visible.
export function LineSeries({
  data,
  series,
  interval,
  label,
  zeroBased = false,
}: {
  data: Row[];
  series: Series[];
  interval: "day" | "week" | "month";
  label: string;
  zeroBased?: boolean;
}) {
  const title = periodTitle(interval);
  return (
    <div className="flex flex-col gap-3">
      <Legend series={series} />
      <div className="h-60 w-full" role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="period"
              tickFormatter={periodTick(interval)}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(v: number) => compact.format(v)}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              width={48}
              domain={zeroBased ? [0, "auto"] : ["auto", "auto"]}
            />
            <Tooltip
              cursor={{ stroke: "var(--axis)" }}
              content={({ active, payload }) => {
                const row = payload?.[0]?.payload as Row | undefined;
                if (!active || !row) return null;
                return (
                  <div className="min-w-36 rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
                    <p className="text-muted">{title(row.period)}</p>
                    {series.map((s) => (
                      <p
                        key={s.key}
                        className="mt-1 flex items-center justify-between gap-4"
                      >
                        <span className="flex items-center gap-1.5 text-ink-2">
                          <span
                            aria-hidden
                            className="h-0.5 w-2.5 rounded-full"
                            style={{ background: s.colour }}
                          />
                          {s.label}
                        </span>
                        <span className="font-medium tabular-nums text-ink">
                          {row[s.key] === null || row[s.key] === undefined
                            ? "–"
                            : count(Number(row[s.key]))}
                        </span>
                      </p>
                    ))}
                  </div>
                );
              }}
            />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.colour}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
