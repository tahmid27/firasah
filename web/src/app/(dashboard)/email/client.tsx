"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { count, rate, ukDate } from "@/lib/format";

type Campaign = {
  campaign_id: string;
  campaign_title: string;
  subject_line: string | null;
  send_time: string | null;
  emails_sent: number;
  open_rate: number | null;
  click_rate: number | null;
  click_to_open_rate: number | null;
  unsubscribes: number | null;
  bounces: number | null;
};

const SHOWN = 10;
const pct = (v: number | null) => (v === null ? "–" : rate(v));

// Selecting a campaign puts it in the URL (?campaign=), so the link-clicks
// card below can show it and the view can be shared.
function useChooseCampaign() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const choose = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("campaign", id);
    startTransition(() =>
      router.push(`${pathname}?${next}#links`, { scroll: false }),
    );
  };
  return { choose, pending };
}

export function CampaignTable({
  rows,
  selected,
}: {
  rows: Campaign[];
  selected: string | null;
}) {
  const [all, setAll] = useState(false);
  const { choose } = useChooseCampaign();
  const visible = all ? rows : rows.slice(0, SHOWN);
  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="py-2 pr-3 font-normal">Campaign</th>
              <th className="hidden py-2 pr-3 text-right font-normal md:table-cell">
                Sent to
              </th>
              <th className="py-2 pr-3 text-right font-normal">Opened</th>
              <th className="py-2 pr-3 text-right font-normal">Clicked</th>
              <th className="hidden py-2 pr-3 text-right font-normal lg:table-cell">
                Clicked after opening
              </th>
              <th className="hidden py-2 pr-3 text-right font-normal sm:table-cell">
                Unsubscribed
              </th>
              <th className="hidden py-2 pr-3 text-right font-normal lg:table-cell">
                Bounced
              </th>
              <th className="py-2 font-normal">
                <span className="sr-only">Links</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((c) => (
              <tr
                key={c.campaign_id}
                className={`border-b border-hairline align-top last:border-0 ${
                  selected === c.campaign_id ? "bg-accent-soft" : ""
                }`}
              >
                <td className="max-w-sm py-2 pr-3">
                  <p className="font-medium">{c.campaign_title}</p>
                  <p className="line-clamp-1 text-xs text-muted">
                    {c.send_time ? ukDate(c.send_time) : "Not sent"}
                    {c.subject_line && ` · ${c.subject_line}`}
                  </p>
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums md:table-cell">
                  {count(c.emails_sent)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {pct(c.open_rate)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {pct(c.click_rate)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums lg:table-cell">
                  {pct(c.click_to_open_rate)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums sm:table-cell">
                  {c.unsubscribes === null ? "–" : count(c.unsubscribes)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums lg:table-cell">
                  {c.bounces === null ? "–" : count(c.bounces)}
                </td>
                <td className="py-2 text-right">
                  <button
                    type="button"
                    onClick={() => choose(c.campaign_id)}
                    className="text-xs text-accent hover:underline"
                  >
                    Links
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > SHOWN && (
        <button
          type="button"
          onClick={() => setAll((a) => !a)}
          className="self-start text-xs text-accent hover:underline"
        >
          {all ? "Show latest 10" : `Show all ${rows.length}`}
        </button>
      )}
    </div>
  );
}

export function CampaignSelect({
  campaigns,
  selected,
}: {
  campaigns: { id: string; label: string }[];
  selected: string;
}) {
  const { choose, pending } = useChooseCampaign();
  return (
    <select
      value={selected}
      disabled={pending}
      onChange={(e) => choose(e.target.value)}
      aria-label="Campaign"
      className="max-w-56 rounded-md border border-border bg-surface px-2 py-1 text-sm text-ink"
    >
      {campaigns.map((c) => (
        <option key={c.id} value={c.id}>
          {c.label}
        </option>
      ))}
    </select>
  );
}

type Hour = { hour: number; opens: number; clicks: number };

function hourLabel(hour: number) {
  if (hour === 0) return "12am";
  if (hour === 12) return "12pm";
  return hour < 12 ? `${hour}am` : `${hour - 12}pm`;
}

// The first hour after sending by which a share (e.g. 80%) of a campaign's
// opens or clicks have arrived.
function hourReaching(
  hours: Hour[],
  measure: "opens" | "clicks",
  share: number,
): Hour | undefined {
  const total = hours.reduce((s, h) => s + h[measure], 0);
  let running = 0;
  for (const h of hours) {
    running += h[measure];
    if (running >= share * total) return h;
  }
  return undefined;
}

const VIEWS = {
  after: { label: "Hours after sending" },
  day: { label: "Time of day" },
} as const;
const MEASURES = { opens: "Opens", clicks: "Clicks" } as const;

// When supporters engage: how quickly after a send (average per campaign),
// or at what time of day (totals, UK time). One measure at a time, since
// clicks are a small fraction of opens.
export function SendTiming({
  afterSend,
  ofDay,
}: {
  afterSend: Hour[];
  ofDay: Hour[];
}) {
  const [view, setView] = useState<keyof typeof VIEWS>("after");
  const [measure, setMeasure] = useState<keyof typeof MEASURES>("opens");
  const data = view === "after" ? afterSend : ofDay;
  const total = data.reduce((s, h) => s + h[measure], 0);

  const most = hourReaching(afterSend, measure, 0.8);

  const toggle = <K extends string>(
    options: Record<K, string | { label: string }>,
    value: K,
    set: (v: K) => void,
    name: string,
  ) => (
    <div
      role="radiogroup"
      aria-label={name}
      className="flex w-fit rounded-md border border-border bg-surface-sunken p-0.5 text-xs"
    >
      {(Object.keys(options) as K[]).map((key) => {
        const option = options[key];
        return (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={value === key}
            onClick={() => set(key)}
            className={`rounded px-2.5 py-1 ${
              value === key
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            {typeof option === "string" ? option : option.label}
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {toggle(VIEWS, view, setView, "View")}
        {toggle(MEASURES, measure, setMeasure, "Measure")}
      </div>
      {view === "after" && most && (
        <p className="text-sm text-ink-2">
          80% of {MEASURES[measure].toLowerCase()} arrive within{" "}
          <span className="font-medium text-ink">
            {most.hour + 1} hour{most.hour === 0 ? "" : "s"}
          </span>{" "}
          of sending.
        </p>
      )}
      <div
        className="h-52 w-full"
        role="img"
        aria-label={`${MEASURES[measure]} by ${VIEWS[view].label.toLowerCase()}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="hour"
              tickFormatter={(h: number) =>
                view === "after" ? `${h}h` : hourLabel(h)
              }
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              interval={view === "after" ? 3 : 2}
            />
            <YAxis
              tickFormatter={(v: number) => count(v)}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
              width={44}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-sunken)" }}
              content={({ active, payload }) => {
                const h = payload?.[0]?.payload as Hour | undefined;
                if (!active || !h) return null;
                const value = h[measure];
                return (
                  <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
                    <p className="text-muted">
                      {view === "after"
                        ? `${h.hour}–${h.hour + 1} hours after sending`
                        : `${hourLabel(h.hour)}–${hourLabel((h.hour + 1) % 24)}, UK time`}
                    </p>
                    <p className="mt-1 font-medium tabular-nums text-ink">
                      {count(value)} {MEASURES[measure].toLowerCase()}
                      {view === "after" ? " per campaign" : ""}
                      {total ? ` · ${Math.round((value / total) * 100)}%` : ""}
                    </p>
                  </div>
                );
              }}
            />
            <Bar
              dataKey={measure}
              fill="var(--series-1)"
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
