"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";

import { count, dayMonth } from "@/lib/format";

type Point = { day: string; value: number | null };

// A small trend line for a stat tile. The y-axis fits the data rather than
// starting at zero, so the shape of a slow change is visible; the tile's own
// number and change carry the scale.
export function Sparkline({ data, label }: { data: Point[]; label: string }) {
  return (
    <div className="h-14 w-full" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
        >
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Tooltip
            cursor={{ stroke: "var(--axis)" }}
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as Point | undefined;
              if (!active || !point || point.value === null) return null;
              return (
                <div className="rounded-md border border-border bg-surface px-2 py-1 text-xs shadow-md">
                  <span className="text-muted">{dayMonth(point.day)}: </span>
                  <span className="font-medium tabular-nums text-ink">
                    {count(point.value)}
                  </span>
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="var(--series-1)"
            strokeWidth={2}
            fill="var(--series-1)"
            fillOpacity={0.12}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
