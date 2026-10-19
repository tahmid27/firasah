import type { Metadata } from "next";
import { Suspense } from "react";

import { Card, CardError, CardSkeleton, attempt } from "@/components/card";
import { HealthBadge } from "@/components/health-badge";
import { PageShell } from "@/components/page-shell";
import { getDataHealth } from "@/lib/api";
import { ago } from "@/lib/format";
import { healthOf } from "@/lib/source-status";

export const metadata: Metadata = { title: "Data health · Firasah" };

export default function DataHealthPage() {
  return (
    <PageShell
      title="Data health"
      description="When each source last updated, and anything that failed."
    >
      <Suspense fallback={<CardSkeleton title="Sources" height="h-64" />}>
        <SourcesCard />
      </Suspense>
      <Card title="What the statuses mean">
        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
          {[
            [
              "ok",
              "New data arrived in the last 30 hours. Firasah refreshes every source once a day, at 6am UK time.",
            ],
            [
              "stale",
              "No new data for over 30 hours, so at least one daily refresh was missed. Numbers may be behind.",
            ],
            [
              "failed",
              "The last refresh hit an error. Earlier data is still shown; nothing is lost.",
            ],
            [
              "manual",
              "LaunchGood has no API, so its data comes from a report someone downloads and uploads. It's only as recent as the last upload.",
            ],
            ["not_connected", "This source isn't linked to your account yet."],
          ].map(([state, text]) => (
            <div key={state} className="flex flex-col gap-1">
              <dt>
                <HealthBadge
                  state={state as Parameters<typeof HealthBadge>[0]["state"]}
                />
              </dt>
              <dd className="text-ink-2">{text}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </PageShell>
  );
}

const when = (timestamp: string | null) =>
  timestamp
    ? new Date(timestamp).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/London",
      })
    : "–";

// D1
async function SourcesCard() {
  const title = "Sources";
  const result = await attempt(getDataHealth);
  if (!result) return <CardError title={title} />;
  return (
    <Card title={title} subtitle="Times are UK time">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="py-2 pr-3 font-normal">Source</th>
              <th className="py-2 pr-3 font-normal">Status</th>
              <th className="py-2 pr-3 font-normal">Latest data</th>
              <th className="hidden py-2 pr-3 font-normal md:table-cell">
                Last refresh
              </th>
              <th className="hidden py-2 pr-3 font-normal md:table-cell">
                Last successful refresh
              </th>
              <th className="hidden py-2 font-normal lg:table-cell">Problem</th>
            </tr>
          </thead>
          <tbody>
            {result.sources.map((s) => (
              <tr
                key={s.source}
                className="border-b border-hairline align-top last:border-0"
              >
                <td className="py-3 pr-3 font-medium">{s.label}</td>
                <td className="py-3 pr-3">
                  <HealthBadge state={healthOf(s)} />
                </td>
                <td className="py-3 pr-3">
                  {s.last_data_at ? (
                    <>
                      <p className="tabular-nums">
                        {when(String(s.last_data_at))}
                      </p>
                      {s.hours_since_data !== null && (
                        <p className="text-xs text-muted">
                          {ago(s.hours_since_data)}
                        </p>
                      )}
                    </>
                  ) : (
                    <span className="text-muted">–</span>
                  )}
                </td>
                <td className="hidden py-3 pr-3 md:table-cell">
                  <p className="tabular-nums">
                    {when(s.last_run_at ? String(s.last_run_at) : null)}
                  </p>
                  {s.last_run_status && (
                    <p className="text-xs capitalize text-muted">
                      {s.last_run_status}
                    </p>
                  )}
                </td>
                <td className="hidden py-3 pr-3 tabular-nums md:table-cell">
                  {when(s.last_success_at ? String(s.last_success_at) : null)}
                </td>
                <td className="hidden py-3 text-ink-2 lg:table-cell">
                  {s.last_run_status === "failed"
                    ? [
                        s.last_error_type,
                        s.last_http_status && `HTTP ${s.last_http_status}`,
                      ]
                        .filter(Boolean)
                        .join(" · ") || "Unknown error"
                    : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
