"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { count, signed } from "@/lib/format";

import { Legend, periodTick, periodTitle } from "./line-series";
import type { Series } from "./stacked-bars";

type Row = { period: string } & Record<string, number | string | null>;

// Gains above the line, losses below it, one bar per series side by side.
// Direction carries the sign; colour stays with the platform.
export function ChangeBars({
  data,
  series,
  interval,
  label,
  signedValues = true,
}: {
  data: Row[];
  series: Series[];
  interval: "day" | "week" | "month";
  label: string;
  // false for plain counts (no + sign on the axis or in the tooltip)
  signedValues?: boolean;
}) {
  const show = (v: number) => (signedValues ? signed(v) : count(Math.abs(v)));
  const title = periodTitle(interval);
  return (
    <div className="flex flex-col gap-3">
      <Legend series={series} />
      <div className="h-60 w-full" role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="period"
              tickFormatter={periodTick(interval)}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={show}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              width={48}
            />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
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
                        <span className="text-ink-2">{s.label}</span>
                        <span className="font-medium tabular-nums text-ink">
                          {row[s.key] === null
                            ? "No reading"
                            : show(Number(row[s.key]))}
                        </span>
                      </p>
                    ))}
                  </div>
                );
              }}
            />
            {series.map((s) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                fill={s.colour}
                radius={[3, 3, 3, 3]}
                maxBarSize={24}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
