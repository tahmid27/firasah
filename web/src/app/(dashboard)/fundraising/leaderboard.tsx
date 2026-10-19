"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";

import { count, gbp, gbpExact, ukDate } from "@/lib/format";
import { platformName } from "@/lib/platforms";

type Row = {
  project_name: string | null;
  fundraiser_name: string;
  source: string;
  raised: number;
  donations: number;
  average_gift: number;
  last_donation_at: string;
};

const SHOWN = 10;

export function ProjectFilter({
  projects,
  selected,
}: {
  projects: string[];
  selected: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  return (
    <label className="flex items-center gap-2 text-xs text-muted">
      Project
      <select
        value={selected ?? ""}
        disabled={pending}
        onChange={(e) => {
          const next = new URLSearchParams(searchParams);
          if (e.target.value) next.set("project", e.target.value);
          else next.delete("project");
          const query = next.toString();
          startTransition(() =>
            router.push(`${pathname}${query ? `?${query}` : ""}#leaderboard`, {
              scroll: false,
            }),
          );
        }}
        className="max-w-48 rounded-md border border-border bg-surface px-2 py-1 text-sm text-ink"
      >
        <option value="">All projects</option>
        {projects.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
    </label>
  );
}

export function LeaderboardTable({
  rows,
  showPlatform,
}: {
  rows: Row[];
  showPlatform: boolean;
}) {
  const [all, setAll] = useState(false);
  const visible = all ? rows : rows.slice(0, SHOWN);

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="py-2 pr-3 font-normal">#</th>
              <th className="py-2 pr-3 font-normal">Fundraiser</th>
              {showPlatform && (
                <th className="hidden py-2 pr-3 font-normal md:table-cell">
                  Platform
                </th>
              )}
              <th className="py-2 pr-3 text-right font-normal">Raised</th>
              <th className="hidden py-2 pr-3 text-right font-normal sm:table-cell">
                Gifts
              </th>
              <th className="hidden py-2 pr-3 text-right font-normal md:table-cell">
                Average gift
              </th>
              <th className="hidden py-2 text-right font-normal lg:table-cell">
                Latest gift
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => (
              <tr
                key={`${row.source}-${row.fundraiser_name}`}
                className="border-b border-hairline last:border-0"
              >
                <td className="py-2 pr-3 align-top text-muted tabular-nums">
                  {index + 1}
                </td>
                <td className="py-2 pr-3">
                  <p className="font-medium">{row.fundraiser_name}</p>
                  {row.project_name && (
                    <p className="text-xs text-muted">{row.project_name}</p>
                  )}
                </td>
                {showPlatform && (
                  <td className="hidden py-2 pr-3 align-top text-ink-2 md:table-cell">
                    {platformName(row.source)}
                  </td>
                )}
                <td className="py-2 pr-3 text-right align-top font-medium tabular-nums">
                  {gbp(row.raised)}
                </td>
                <td className="hidden py-2 pr-3 text-right align-top tabular-nums sm:table-cell">
                  {count(row.donations)}
                </td>
                <td className="hidden py-2 pr-3 text-right align-top tabular-nums md:table-cell">
                  {gbpExact(row.average_gift)}
                </td>
                <td className="hidden py-2 text-right align-top text-ink-2 lg:table-cell">
                  {ukDate(row.last_donation_at)}
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
