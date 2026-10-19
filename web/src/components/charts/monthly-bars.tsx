"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { gbp, gbpShort, monthShort, monthYear } from "@/lib/format";

export type MonthlyPoint = { period: string; value: number; partial: boolean };

// Monthly totals as bars. The current, unfinished month is drawn lighter and
// labelled "so far", so it doesn't read as a drop.
export function MonthlyBars({
  data,
  label,
}: {
  data: MonthlyPoint[];
  label: string;
}) {
  return (
    <div className="h-56 w-full" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis
            dataKey="period"
            tickFormatter={monthShort}
            tickLine={false}
            axisLine={{ stroke: "var(--axis)" }}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={gbpShort}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            width={56}
          />
          <Tooltip
            cursor={{ fill: "var(--surface-sunken)" }}
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as MonthlyPoint | undefined;
              if (!active || !point) return null;
              return (
                <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
                  <p className="text-muted">
                    {monthYear(point.period)}
                    {point.partial && " (so far)"}
                  </p>
                  <p className="mt-0.5 text-sm font-medium tabular-nums text-ink">
                    {gbp(point.value)}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((point) => (
              <Cell
                key={point.period}
                fill="var(--series-1)"
                fillOpacity={point.partial ? 0.4 : 1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
