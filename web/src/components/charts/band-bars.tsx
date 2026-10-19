"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { count, gbp, gbpShort } from "@/lib/format";

export type Band = { band: string; donations: number; raised: number };

const MEASURES = {
  donations: { label: "Number of gifts", format: count, axis: count },
  raised: { label: "Amount raised", format: gbp, axis: gbpShort },
} as const;

// Gift-size bands, switchable between how many gifts and how much money:
// small gifts are usually most of the count but not most of the money.
export function BandBars({ data }: { data: Band[] }) {
  const [measure, setMeasure] = useState<keyof typeof MEASURES>("donations");
  const { axis } = MEASURES[measure];
  const total = data.reduce((sum, b) => sum + b[measure], 0);

  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="Show"
        className="flex w-fit rounded-md border border-border bg-surface-sunken p-0.5 text-xs"
      >
        {(Object.keys(MEASURES) as (keyof typeof MEASURES)[]).map((key) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={measure === key}
            onClick={() => setMeasure(key)}
            className={`rounded px-2.5 py-1 ${
              measure === key
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            {MEASURES[key].label}
          </button>
        ))}
      </div>
      <div
        className="h-56 w-full"
        role="img"
        aria-label={`Gift sizes by ${MEASURES[measure].label.toLowerCase()}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 0, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="band"
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              interval={0}
            />
            <YAxis
              tickFormatter={axis}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              width={56}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
              content={({ active, payload }) => {
                const band = payload?.[0]?.payload as Band | undefined;
                if (!active || !band) return null;
                return (
                  <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
                    <p className="text-muted">Gifts of {band.band}</p>
                    <p className="mt-1 tabular-nums text-ink">
                      {count(band.donations)} gifts
                    </p>
                    <p className="tabular-nums text-ink">
                      {gbp(band.raised)} raised
                    </p>
                  </div>
                );
              }}
            />
            <Bar
              dataKey={measure}
              fill="var(--series-1)"
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
              isAnimationActive={false}
            >
              <LabelList
                dataKey={measure}
                position="top"
                formatter={(value) =>
                  total ? `${Math.round((Number(value) / total) * 100)}%` : ""
                }
                style={{ fill: "var(--ink-2)", fontSize: 11 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
