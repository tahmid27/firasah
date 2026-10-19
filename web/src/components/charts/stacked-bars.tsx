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

import { dayMonth, gbp, gbpShort, monthShort, monthYear } from "@/lib/format";

export type Series = { key: string; label: string; colour: string };
export type StackedRow = { period: string; partial: boolean } & Record<
  string,
  number | string | boolean
>;

// Money per period, one stacked colour per series. Periods only partly inside
// the range (or not finished yet) are drawn lighter and marked in the tooltip.
export function StackedBars({
  data,
  series,
  interval,
  label,
}: {
  data: StackedRow[];
  series: Series[];
  interval: "week" | "month";
  label: string;
}) {
  const tick = (p: string) =>
    interval === "month" ? monthShort(p) : dayMonth(p);
  const title = (p: string) =>
    interval === "month"
      ? monthYear(p)
      : `Week of ${dayMonth(p)} ${p.slice(0, 4)}`;

  return (
    <div className="flex flex-col gap-3">
      {series.length > 1 && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
          {series.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="size-2.5 rounded-sm"
                style={{ background: s.colour }}
              />
              {s.label}
            </li>
          ))}
        </ul>
      )}
      <div className="h-64 w-full" role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="period"
              tickFormatter={tick}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              interval="preserveStartEnd"
              minTickGap={16}
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
                const row = payload?.[0]?.payload as StackedRow | undefined;
                if (!active || !row) return null;
                const total = series.reduce(
                  (sum, s) => sum + Number(row[s.key] ?? 0),
                  0,
                );
                return (
                  <div className="min-w-40 rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
                    <p className="text-muted">
                      {title(row.period)}
                      {row.partial && " (part only)"}
                    </p>
                    {series.length > 1 &&
                      series.map((s) => (
                        <p
                          key={s.key}
                          className="mt-1 flex items-center justify-between gap-4"
                        >
                          <span className="flex items-center gap-1.5 text-ink-2">
                            <span
                              aria-hidden
                              className="size-2 rounded-sm"
                              style={{ background: s.colour }}
                            />
                            {s.label}
                          </span>
                          <span className="tabular-nums text-ink">
                            {gbp(Number(row[s.key] ?? 0))}
                          </span>
                        </p>
                      ))}
                    <p className="mt-1 flex justify-between gap-4 text-sm font-medium text-ink">
                      {series.length > 1 && <span>Total</span>}
                      <span className="tabular-nums">{gbp(total)}</span>
                    </p>
                  </div>
                );
              }}
            />
            {series.map((s, index) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                stackId="total"
                fill={s.colour}
                stroke="var(--surface)"
                strokeWidth={series.length > 1 ? 1 : 0}
                radius={index === series.length - 1 ? [4, 4, 0, 0] : 0}
                maxBarSize={40}
                isAnimationActive={false}
              >
                {data.map((row) => (
                  <Cell key={row.period} fillOpacity={row.partial ? 0.4 : 1} />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
