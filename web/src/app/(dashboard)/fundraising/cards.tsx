import Link from "next/link";

import { Card, CardError, attempt } from "@/components/card";
import { BandBars } from "@/components/charts/band-bars";
import { Heatmap } from "@/components/charts/heatmap";
import { StackedBars } from "@/components/charts/stacked-bars";
import { Delta } from "@/components/delta";
import { apiClient, connectedSources, unwrap } from "@/lib/api";
import { count, gbp, gbpExact, percent, rate } from "@/lib/format";
import { PLATFORM_COLOURS, platformName, trafficLabel } from "@/lib/platforms";
import {
  intervalFor,
  param,
  previousRange,
  rangeFrom,
  type SearchParams,
} from "@/lib/range-server";

import { LeaderboardTable, ProjectFilter } from "./leaderboard";

type Props = { searchParams: SearchParams };

async function giftSizes(start: string, end: string) {
  const api = await apiClient();
  return unwrap(
    await api.GET("/fundraising/gift-sizes", {
      params: { query: { start, end } },
    }),
  );
}

function totalsOf(bands: { donations: number; raised: number }[]) {
  const raised = bands.reduce((s, b) => s + b.raised, 0);
  const donations = bands.reduce((s, b) => s + b.donations, 0);
  return { raised, donations, average: donations ? raised / donations : null };
}

function change(now: number | null, before: number | null) {
  if (now === null || !before) return null;
  return ((now - before) / before) * 100;
}

// Totals for the range, against the same number of days just before it.
// Built from the gift-size bands, which already cover every GBP gift.
export async function TotalsTiles({ searchParams }: Props) {
  const range = await rangeFrom(searchParams);
  const before = previousRange(range);
  const result = await attempt(async () => {
    const [now, then] = await Promise.all([
      giftSizes(range.start, range.end),
      giftSizes(before.start, before.end),
    ]);
    return { now: totalsOf(now.bands), then: totalsOf(then.bands) };
  });
  if (!result) {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        <CardError title="Raised" />
      </div>
    );
  }
  const { now, then } = result;
  const days =
    (Date.parse(range.end) - Date.parse(range.start)) / 86_400_000 + 1;
  const vs = `vs the ${count(days)} days before`;
  const tiles = [
    {
      title: "Raised",
      value: gbp(now.raised),
      pct: change(now.raised, then.raised),
      was: gbp(then.raised),
    },
    {
      title: "Gifts",
      value: count(now.donations),
      pct: change(now.donations, then.donations),
      was: count(then.donations),
    },
    {
      title: "Average gift",
      value: now.average === null ? "–" : gbpExact(now.average),
      pct: change(now.average, then.average),
      was: then.average === null ? "–" : gbpExact(then.average),
    },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {tiles.map((tile) => (
        <Card key={tile.title} title={tile.title} subtitle={range.label}>
          <div>
            <p className="text-3xl font-semibold tracking-tight">
              {tile.value}
            </p>
            <Delta pct={tile.pct} label={`${vs} (${tile.was})`} />
          </div>
        </Card>
      ))}
    </div>
  );
}

function isPartial(
  period: string,
  index: number,
  last: number,
  interval: "week" | "month",
  start: string,
  end: string,
) {
  const day = 86_400_000;
  const periodStart = Date.parse(period);
  let periodEnd: number;
  if (interval === "week") {
    periodEnd = periodStart + 6 * day;
  } else {
    const d = new Date(periodStart);
    periodEnd = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0);
  }
  return (
    (index === 0 && Date.parse(start) > periodStart) ||
    (index === last && Date.parse(end) < periodEnd)
  );
}

// F1
export async function IncomeCard({ searchParams }: Props) {
  const title = "Income over time";
  const range = await rangeFrom(searchParams);
  const interval = intervalFor(range);
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(
      await api.GET("/fundraising/income-over-time", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
    );
  });
  if (!result) return <CardError title={title} />;

  const series = result.series.map((s) => ({
    key: s.key,
    label: s.label,
    colour: PLATFORM_COLOURS[s.key] ?? "var(--series-3)",
  }));
  const last = result.data.length - 1;
  const data = result.data.map((row, index) => {
    const period = String(row.period);
    return {
      ...row,
      period,
      partial: isPartial(period, index, last, interval, range.start, range.end),
    };
  });
  return (
    <Card
      title={title}
      subtitle={`${interval === "week" ? "Weekly" : "Monthly"} · ${range.label} · periods only partly in range shown lighter`}
    >
      {series.length === 0 ? (
        <p className="text-sm text-ink-2">No donations in this period.</p>
      ) : (
        <StackedBars
          data={data}
          series={series}
          interval={interval}
          label={`${interval === "week" ? "Weekly" : "Monthly"} income, ${range.label}`}
        />
      )}
    </Card>
  );
}

// F3
export async function ProjectsCard({ searchParams }: Props) {
  const title = "Projects";
  const range = await rangeFrom(searchParams);
  const params = await searchParams;
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(
      await api.GET("/fundraising/projects", {
        params: { query: { start: range.start, end: range.end } },
      }),
    );
  });
  if (!result) return <CardError title={title} />;

  const total = result.rows.reduce((s, r) => s + r.raised, 0);
  const link = (project: string) => {
    const next = new URLSearchParams();
    for (const key of ["range", "from", "to"]) {
      const value = param(params, key);
      if (value) next.set(key, value);
    }
    next.set("project", project);
    return `?${next}#leaderboard`;
  };
  return (
    <Card
      title={title}
      subtitle={`${range.label} · select one to see its fundraisers`}
    >
      {result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No donations in this period.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-hairline">
          {result.rows.map((row) => (
            <li
              key={row.project_name ?? "none"}
              className="flex items-center justify-between gap-3 py-2"
            >
              <div className="min-w-0">
                {row.project_name ? (
                  <Link
                    href={link(row.project_name)}
                    scroll={false}
                    className="font-medium hover:underline"
                  >
                    {row.project_name}
                  </Link>
                ) : (
                  <p className="font-medium">No project</p>
                )}
                <p className="text-xs text-muted">
                  {count(row.donations)} gifts · {row.fundraisers} fundraiser
                  {row.fundraisers === 1 ? "" : "s"} ·{" "}
                  {row.sources.map(platformName).join(", ")}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-medium tabular-nums">
                  {gbp(row.raised)}
                </p>
                <p className="text-xs text-muted tabular-nums">
                  {total ? percent((row.raised / total) * 100, 0) : "–"}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// F9
export async function TargetsCard() {
  const title = "Progress against targets";
  const result = await attempt(async () => {
    const api = await apiClient();
    const [targets, connected] = await Promise.all([
      api.GET("/fundraising/targets"),
      connectedSources(),
    ]);
    return { rows: unwrap(targets).rows, connected };
  });
  if (!result) return <CardError title={title} />;

  return (
    <Card
      title={title}
      subtitle="JustGiving pages with a target · all-time totals"
    >
      {!result.connected.has("justgiving") ? (
        <p className="text-sm text-ink-2">
          Targets come from JustGiving pages. LaunchGood exports don&apos;t
          include them.
        </p>
      ) : result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">
          None of your JustGiving pages has a target.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {result.rows.map((row) => (
            <li key={row.fundraiser_name} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0">
                  <span className="font-medium">{row.fundraiser_name}</span>
                  {row.page_status && row.page_status !== "Active" && (
                    <span className="ml-2 text-xs text-muted">
                      {row.page_status}
                    </span>
                  )}
                </span>
                <span className="shrink-0 font-medium tabular-nums">
                  {percent(row.progress_pct, 0)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-sunken" aria-hidden>
                <div
                  className="h-full rounded-full bg-series-1"
                  style={{ width: `${Math.min(100, row.progress_pct)}%` }}
                />
              </div>
              <p className="text-xs text-muted tabular-nums">
                {gbp(row.raised)} of {gbp(row.target)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// F2
export async function LeaderboardCard({ searchParams }: Props) {
  const title = "Fundraiser leaderboard";
  const range = await rangeFrom(searchParams);
  const project = param(await searchParams, "project") ?? null;
  const result = await attempt(async () => {
    const api = await apiClient();
    const [board, projects] = await Promise.all([
      api.GET("/fundraising/fundraisers", {
        params: {
          query: {
            start: range.start,
            end: range.end,
            limit: 50,
            ...(project ? { project } : {}),
          },
        },
      }),
      api.GET("/fundraising/projects", {
        params: { query: { start: range.start, end: range.end } },
      }),
    ]);
    return { rows: unwrap(board).rows, projects: unwrap(projects).rows };
  });
  if (!result) return <CardError title={title} />;

  const projectNames = result.projects
    .map((p) => p.project_name)
    .filter((p): p is string => !!p);
  if (project && !projectNames.includes(project)) projectNames.unshift(project);
  const platforms = new Set(result.rows.map((r) => r.source));
  return (
    <Card
      title={title}
      subtitle={`${range.label}${project ? ` · ${project}` : ""}`}
      action={<ProjectFilter projects={projectNames} selected={project} />}
    >
      {result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No donations in this period.</p>
      ) : (
        <LeaderboardTable
          key={`${project}|${range.start}|${range.end}`}
          rows={result.rows.map((r) => ({
            ...r,
            last_donation_at: String(r.last_donation_at),
          }))}
          showPlatform={platforms.size > 1}
        />
      )}
    </Card>
  );
}

// F8
export async function TrafficCard({ searchParams }: Props) {
  const title = "Where gifts came from";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(
      await api.GET("/fundraising/traffic-sources", {
        params: { query: { start: range.start, end: range.end } },
      }),
    );
  });
  if (!result) return <CardError title={title} />;

  const total = result.rows.reduce((s, r) => s + r.raised, 0);
  const many = new Set(result.rows.map((r) => r.source)).size > 1;
  const TOP = 7;
  const top = result.rows.slice(0, TOP);
  const rest = result.rows.slice(TOP);
  const rows = top.map((r) => ({
    label: trafficLabel(r.source, r.traffic_source),
    platform: many ? platformName(r.source) : null,
    raised: r.raised,
    donations: r.donations,
  }));
  if (rest.length) {
    rows.push({
      label: `Other (${rest.length})`,
      platform: null,
      raised: rest.reduce((s, r) => s + r.raised, 0),
      donations: rest.reduce((s, r) => s + r.donations, 0),
    });
  }
  return (
    <Card
      title={title}
      subtitle={`As recorded by each platform · ${range.label}`}
    >
      {rows.length === 0 ? (
        <p className="text-sm text-ink-2">No donations in this period.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.map((row) => (
            <li
              key={`${row.platform}-${row.label}`}
              className="flex flex-col gap-1"
            >
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0">
                  <span className="font-medium">{row.label}</span>
                  {row.platform && (
                    <span className="ml-2 text-xs text-muted">
                      {row.platform}
                    </span>
                  )}
                </span>
                <span className="shrink-0 tabular-nums">
                  <span className="font-medium">{gbp(row.raised)}</span>
                  <span className="ml-2 text-xs text-muted">
                    {total ? percent((row.raised / total) * 100, 0) : ""}
                  </span>
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-sunken" aria-hidden>
                <div
                  className="h-full rounded-full bg-series-1"
                  style={{
                    width: `${total ? (row.raised / (rows[0]?.raised || 1)) * 100 : 0}%`,
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// F4
export async function GiftSizesCard({ searchParams }: Props) {
  const title = "Gift sizes";
  const range = await rangeFrom(searchParams);
  const result = await attempt(() => giftSizes(range.start, range.end));
  if (!result) return <CardError title={title} />;

  const any = result.bands.some((b) => b.donations > 0);
  return (
    <Card title={title} subtitle={range.label}>
      {any ? (
        <BandBars data={result.bands} />
      ) : (
        <p className="text-sm text-ink-2">No donations in this period.</p>
      )}
    </Card>
  );
}

// F10
export async function TimingCard({ searchParams }: Props) {
  const title = "When people give";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(
      await api.GET("/fundraising/timing", {
        params: { query: { start: range.start, end: range.end } },
      }),
    );
  });
  if (!result) return <CardError title={title} />;

  return (
    <Card
      title={title}
      subtitle={`Number of gifts by day and hour, UK time · ${range.label}`}
    >
      <Heatmap cells={result.cells} unit="gifts" />
    </Card>
  );
}

function NotApplicable({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-ink-2">{children}</p>;
}

// F5
export async function GiftAidCard({ searchParams }: Props) {
  const title = "Gift Aid";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () => {
    const api = await apiClient();
    const [giftAid, connected] = await Promise.all([
      api.GET("/fundraising/gift-aid", {
        params: { query: { start: range.start, end: range.end } },
      }),
      connectedSources(),
    ]);
    return { giftAid: unwrap(giftAid), connected };
  });
  if (!result) return <CardError title={title} />;
  const { giftAid, connected } = result;

  return (
    <Card title={title} subtitle="25% of eligible gifts, reclaimed from HMRC">
      {connected.has("launchgood") && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-muted">LaunchGood · {range.label}</p>
          <p className="text-2xl font-semibold tracking-tight">
            {gbp(giftAid.claim_value)}
          </p>
          <p className="text-xs text-ink-2">
            to claim on {gbp(giftAid.eligible_amount)} of eligible gifts
            {giftAid.gift_aid_share_pct !== null &&
              ` · ${percent(giftAid.gift_aid_share_pct, 0)} of gifts had Gift Aid`}
          </p>
        </div>
      )}
      {connected.has("justgiving") && (
        <div className="flex flex-col gap-1 border-t border-hairline pt-3 first:border-0 first:pt-0">
          <p className="text-xs text-muted">JustGiving · all pages, all time</p>
          <p className="text-2xl font-semibold tracking-tight">
            {gbp(giftAid.justgiving_estimated_gift_aid)}
          </p>
          <p className="text-xs text-ink-2">
            JustGiving&apos;s own estimate. It claims Gift Aid for you and
            doesn&apos;t share it per gift, so it can&apos;t follow the date
            range.
          </p>
        </div>
      )}
      {!connected.has("launchgood") && !connected.has("justgiving") && (
        <NotApplicable>No fundraising platform connected.</NotApplicable>
      )}
    </Card>
  );
}

// F6
export async function ZakatCard({ searchParams }: Props) {
  const title = "Zakat";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () => {
    const api = await apiClient();
    const [zakat, connected] = await Promise.all([
      api.GET("/fundraising/zakat", {
        params: { query: { start: range.start, end: range.end } },
      }),
      connectedSources(),
    ]);
    return { zakat: unwrap(zakat), connected };
  });
  if (!result) return <CardError title={title} />;
  const { zakat, connected } = result;

  return (
    <Card title={title} subtitle={`LaunchGood · ${range.label}`}>
      {!connected.has("launchgood") ? (
        <NotApplicable>
          Zakat is recorded on LaunchGood gifts. JustGiving doesn&apos;t mark
          gifts as Zakat.
        </NotApplicable>
      ) : zakat.donations === 0 ? (
        <NotApplicable>No Zakat gifts in this period.</NotApplicable>
      ) : (
        <>
          <div>
            <p className="text-2xl font-semibold tracking-tight">
              {gbp(zakat.total_zakat)}
            </p>
            <p className="text-xs text-ink-2">
              from {count(zakat.donations)} gifts
            </p>
          </div>
          <ul className="flex flex-col divide-y divide-hairline text-sm">
            {zakat.by_project.map((p) => (
              <li
                key={p.project_name ?? "none"}
                className="flex justify-between gap-3 py-1.5"
              >
                <span className="min-w-0 truncate text-ink-2">
                  {p.project_name ?? "No project"}
                </span>
                <span className="shrink-0 tabular-nums">{gbp(p.zakat)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}

// F7
export async function FeesCard({ searchParams }: Props) {
  const title = "Platform fees";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () => {
    const api = await apiClient();
    const [fees, connected] = await Promise.all([
      api.GET("/fundraising/fees", {
        params: { query: { start: range.start, end: range.end } },
      }),
      connectedSources(),
    ]);
    return { fees: unwrap(fees), connected };
  });
  if (!result) return <CardError title={title} />;
  const { fees, connected } = result;
  const sum = (key: string) =>
    fees.data.reduce((s, row) => s + Number(row[key] ?? 0), 0);
  const gross = sum("gross");
  const paid = sum("fees");
  const net = sum("net");

  return (
    <Card title={title} subtitle={`LaunchGood · ${range.label}`}>
      {!connected.has("launchgood") ? (
        <NotApplicable>
          Fees are only reported by LaunchGood. JustGiving doesn&apos;t include
          them in its data.
        </NotApplicable>
      ) : gross === 0 ? (
        <NotApplicable>No LaunchGood gifts in this period.</NotApplicable>
      ) : (
        <>
          <div>
            <p className="text-2xl font-semibold tracking-tight">{gbp(paid)}</p>
            <p className="text-xs text-ink-2">
              in fees · {rate(paid / gross)} of what donors gave
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-3 border-t border-hairline pt-3 text-sm">
            <div>
              <dt className="text-xs text-muted">Donors gave</dt>
              <dd className="font-medium tabular-nums">{gbp(gross)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">You received</dt>
              <dd className="font-medium tabular-nums">{gbp(net)}</dd>
            </div>
          </dl>
        </>
      )}
    </Card>
  );
}
