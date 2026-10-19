"use client";

import { ExternalLink } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";

import { LineSeries } from "@/components/charts/line-series";
import type { Series } from "@/components/charts/stacked-bars";
import { count, rate, ukDate } from "@/lib/format";
import { platformName } from "@/lib/platforms";
import { SORTS, type Sort } from "@/lib/post-sorts";

type Post = {
  post_id: string;
  platform: string;
  posted_at: string;
  format: string;
  caption: string | null;
  permalink: string | null;
  views: number | null;
  reach: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
  engagement_rate: number | null;
};

const SHOWN = 10;
const n = (value: number | null) => (value === null ? "–" : count(value));

export function SortSelect({ selected }: { selected: Sort }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  return (
    <label className="flex items-center gap-2 text-xs text-muted">
      Sort by
      <select
        value={selected}
        disabled={pending}
        onChange={(e) => {
          const next = new URLSearchParams(searchParams);
          if (e.target.value === "engagement_rate") next.delete("sort");
          else next.set("sort", e.target.value);
          const query = next.toString();
          startTransition(() =>
            router.push(`${pathname}${query ? `?${query}` : ""}#posts`, {
              scroll: false,
            }),
          );
        }}
        className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-ink"
      >
        {Object.entries(SORTS).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function PostsTable({ rows }: { rows: Post[] }) {
  const [all, setAll] = useState(false);
  const visible = all ? rows : rows.slice(0, SHOWN);
  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="py-2 pr-3 font-normal">Post</th>
              <th className="py-2 pr-3 text-right font-normal">Reach</th>
              <th className="hidden py-2 pr-3 text-right font-normal sm:table-cell">
                Views
              </th>
              <th className="hidden py-2 pr-3 text-right font-normal md:table-cell">
                Likes
              </th>
              <th className="hidden py-2 pr-3 text-right font-normal md:table-cell">
                Comments
              </th>
              <th className="py-2 text-right font-normal">Engagement</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((post) => (
              <tr
                key={post.post_id}
                className="border-b border-hairline align-top last:border-0"
              >
                <td className="max-w-md py-2 pr-3">
                  <p className="line-clamp-2">{post.caption || "No caption"}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted">
                    {platformName(post.platform)} · {post.format} ·{" "}
                    {ukDate(post.posted_at)}
                    {post.permalink && (
                      <a
                        href={post.permalink}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-0.5 text-accent hover:underline"
                      >
                        Open <ExternalLink size={11} aria-hidden />
                      </a>
                    )}
                  </p>
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {n(post.reach)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums sm:table-cell">
                  {n(post.views)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums md:table-cell">
                  {n(post.likes)}
                </td>
                <td className="hidden py-2 pr-3 text-right tabular-nums md:table-cell">
                  {n(post.comments)}
                </td>
                <td className="py-2 text-right font-medium tabular-nums">
                  {post.engagement_rate === null
                    ? "–"
                    : rate(post.engagement_rate)}
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
          {all ? "Show top 10" : `Show all ${rows.length}`}
        </button>
      )}
    </div>
  );
}

// One Instagram measure at a time: they differ by orders of magnitude, so
// several on one axis would flatten the smaller ones (and two axes mislead).
export function ActivityChart({
  data,
  series,
  interval,
}: {
  data: ({ period: string } & Record<string, number | string | null>)[];
  series: { key: string; label: string }[];
  interval: "day" | "week" | "month";
}) {
  const [key, setKey] = useState(series[0]?.key ?? "reach");
  const chosen = series.find((s) => s.key === key) ?? series[0];
  const line: Series[] = chosen
    ? [{ key: chosen.key, label: chosen.label, colour: "var(--series-1)" }]
    : [];
  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="Measure"
        className="flex w-fit flex-wrap rounded-md border border-border bg-surface-sunken p-0.5 text-xs"
      >
        {series.map((s) => (
          <button
            key={s.key}
            type="button"
            role="radio"
            aria-checked={key === s.key}
            onClick={() => setKey(s.key)}
            className={`rounded px-2.5 py-1 ${
              key === s.key
                ? "bg-surface text-ink shadow-xs"
                : "text-muted hover:text-ink"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <LineSeries
        data={data}
        series={line}
        interval={interval}
        label={`Instagram ${chosen?.label.toLowerCase()} over time`}
        zeroBased
      />
    </div>
  );
}
