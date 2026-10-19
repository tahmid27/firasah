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

import { periodTick, periodTitle } from "@/components/charts/line-series";
import { count, gbp, gbpShort } from "@/lib/format";

export type Period = {
  period: string;
  raised: number;
  emails: string[];
  posts: number;
};

// Daily (or weekly) donations with every email as a dashed line and posts as
// a strip underneath, sharing one hover. Shows what went out around a rise,
// not that it caused it.
export function Timeline({
  data,
  interval,
}: {
  data: Period[];
  interval: "day" | "week";
}) {
  const title = periodTitle(interval);
  const tick = periodTick(interval);
  const emailPeriods = data.filter((p) => p.emails.length > 0);

  const tooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: readonly { payload?: unknown }[];
  }) => {
    const p = payload?.[0]?.payload as Period | undefined;
    if (!active || !p) return null;
    return (
      <div className="max-w-64 rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
        <p className="text-muted">{title(p.period)}</p>
        <p className="mt-1 text-sm font-medium tabular-nums text-ink">
          {gbp(p.raised)} raised
        </p>
        {p.emails.map((e, i) => (
          <p key={i} className="mt-1 flex gap-1.5 text-ink-2">
            <span
              aria-hidden
              className="mt-1.5 h-0.5 w-2.5 shrink-0 bg-series-2"
            />
            Email: {e}
          </p>
        ))}
        {p.posts > 0 && (
          <p className="mt-1 text-ink-2">
            {count(p.posts)} post{p.posts === 1 ? "" : "s"}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-sm bg-series-1" />
          Donations
        </li>
        <li className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="h-3 w-0 border-l-2 border-dashed border-series-2"
          />
          Email sent
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-sm bg-muted/45" />
          Posts (strip below)
        </li>
      </ul>
      <div
        className="h-64 w-full"
        role="img"
        aria-label="Donations over time with emails marked"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            syncId="appeal"
            margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="period" hide />
            <YAxis
              tickFormatter={gbpShort}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              width={56}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
              content={tooltip}
            />
            {emailPeriods.map((p) => (
              <ReferenceLine
                key={p.period}
                x={p.period}
                stroke="var(--series-2)"
                strokeDasharray="3 3"
                strokeWidth={1.5}
              />
            ))}
            <Bar
              dataKey="raised"
              fill="var(--series-1)"
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="h-14 w-full" role="img" aria-label="Posts per period">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            syncId="appeal"
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          >
            <XAxis
              dataKey="period"
              tickFormatter={tick}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              minTickGap={24}
            />
            <YAxis hide />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
              content={tooltip}
            />
            <Bar
              dataKey="posts"
              fill="var(--muted)"
              fillOpacity={0.45}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
