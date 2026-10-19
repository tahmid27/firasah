"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { count, monthShort, monthYear } from "@/lib/format";

type Point = { period: string; value: number | null };

// One small monthly count chart with its own scale. Used side by side
// (small multiples) when measures differ too much in size to share an axis.
export function MiniBars({
  title,
  data,
  colour = "var(--series-1)",
}: {
  title: string;
  data: Point[];
  colour?: string;
}) {
  const total = data.reduce((s, p) => s + (p.value ?? 0), 0);
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <p className="flex items-baseline justify-between gap-2 text-xs">
        <span className="font-medium text-ink-2">{title}</span>
        <span className="tabular-nums text-muted">{count(total)} total</span>
      </p>
      <div className="h-28 w-full" role="img" aria-label={`${title} per month`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
          >
            <XAxis
              dataKey="period"
              tickFormatter={monthShort}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              interval="preserveStartEnd"
              minTickGap={12}
            />
            <YAxis
              tickFormatter={(v: number) => count(v)}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              width={36}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as Point | undefined;
                if (!active || !p) return null;
                return (
                  <div className="rounded-md border border-border bg-surface px-2 py-1 text-xs shadow-md">
                    <span className="text-muted">{monthYear(p.period)}: </span>
                    <span className="font-medium tabular-nums text-ink">
                      {p.value === null ? "No data" : count(p.value)}
                    </span>
                  </div>
                );
              }}
            />
            <Bar
              dataKey="value"
              fill={colour}
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
