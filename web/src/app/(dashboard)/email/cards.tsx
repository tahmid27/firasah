import { Card, CardError, attempt } from "@/components/card";
import { ChangeBars } from "@/components/charts/change-bars";
import { MiniBars } from "@/components/charts/mini-bars";
import { Delta } from "@/components/delta";
import { apiClient, connectedSources, unwrap } from "@/lib/api";
import { count, rate, ukDate } from "@/lib/format";
import {
  param,
  previousRange,
  rangeFrom,
  type SearchParams,
} from "@/lib/range-server";

import { CampaignSelect, CampaignTable, SendTiming } from "./client";

type Props = { searchParams: SearchParams };
const DAY = 86_400_000;

async function campaignsIn(start: string, end: string) {
  const api = await apiClient();
  return unwrap(
    await api.GET("/email/campaigns", {
      params: { query: { start, end, limit: 200 } },
    }),
  ).rows;
}

type Campaigns = Awaited<ReturnType<typeof campaignsIn>>;

function totals(rows: Campaigns) {
  const sent = rows.reduce((s, r) => s + r.emails_sent, 0);
  const opens = rows.reduce((s, r) => s + (r.unique_opens ?? 0), 0);
  const clicks = rows.reduce((s, r) => s + (r.unique_clicks ?? 0), 0);
  const unsubscribes = rows.reduce((s, r) => s + (r.unsubscribes ?? 0), 0);
  return {
    campaigns: rows.length,
    openRate: sent ? opens / sent : null,
    clickRate: sent ? clicks / sent : null,
    unsubscribes,
  };
}

function change(now: number | null, before: number | null) {
  if (now === null || !before) return null;
  return ((now - before) / before) * 100;
}

function NotConnected() {
  return <p className="text-sm text-ink-2">Mailchimp isn&apos;t connected.</p>;
}

// Campaigns sent, open rate, click rate, unsubscribes: vs the period before
export async function EmailTotals({ searchParams }: Props) {
  const range = await rangeFrom(searchParams);
  const before = previousRange(range);
  const days = (Date.parse(range.end) - Date.parse(range.start)) / DAY + 1;
  const result = await attempt(async () => {
    const [now, then] = await Promise.all([
      campaignsIn(range.start, range.end),
      campaignsIn(before.start, before.end),
    ]);
    return { now: totals(now), then: totals(then) };
  });
  if (!result) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <CardError title="Campaigns sent" />
      </div>
    );
  }
  const { now, then } = result;
  const vs = `vs the ${count(days)} days before`;
  const tiles = [
    {
      title: "Campaigns sent",
      value: count(now.campaigns),
      pct: change(now.campaigns, then.campaigns),
      was: count(then.campaigns),
    },
    {
      title: "Open rate",
      value: now.openRate === null ? "–" : rate(now.openRate),
      pct: change(now.openRate, then.openRate),
      was: then.openRate === null ? "–" : rate(then.openRate),
    },
    {
      title: "Click rate",
      value: now.clickRate === null ? "–" : rate(now.clickRate),
      pct: change(now.clickRate, then.clickRate),
      was: then.clickRate === null ? "–" : rate(then.clickRate),
    },
    {
      title: "Unsubscribes",
      lowerIsBetter: true,
      value: count(now.unsubscribes),
      pct: change(now.unsubscribes, then.unsubscribes),
      was: count(then.unsubscribes),
    },
  ];
  return (
    <div className="flex flex-col gap-2">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((tile) => (
          <Card key={tile.title} title={tile.title} subtitle={range.label}>
            <div>
              <p className="font-heading text-3xl font-bold tracking-tight">
                {tile.value}
              </p>
              <Delta
                pct={tile.pct}
                label={`${vs} (${tile.was})`}
                lowerIsBetter={"lowerIsBetter" in tile && tile.lowerIsBetter}
              />
            </div>
          </Card>
        ))}
      </div>
      <p className="text-xs text-muted">
        Open rates are approximate. Apple Mail opens emails automatically, which
        adds opens nobody made, and junk folders block the tracking image, which
        hides real ones. Clicks are the more reliable signal.
      </p>
    </div>
  );
}

// E1
export async function CampaignsCard({ searchParams }: Props) {
  const title = "Campaigns";
  const range = await rangeFrom(searchParams);
  const selected = param(await searchParams, "campaign") ?? null;
  const result = await attempt(async () => {
    const [rows, connected] = await Promise.all([
      campaignsIn(range.start, range.end),
      connectedSources(),
    ]);
    return { rows, connected };
  });
  if (!result) return <CardError title={title} />;
  return (
    <Card title={title} subtitle={`Sent ${range.label} · newest first`}>
      {!result.connected.has("mailchimp") ? (
        <NotConnected />
      ) : result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No campaigns sent in this period.</p>
      ) : (
        <CampaignTable
          key={`${range.start}|${range.end}`}
          rows={result.rows.map((r) => ({
            ...r,
            send_time: r.send_time ? String(r.send_time) : null,
          }))}
          selected={selected ?? result.rows[0].campaign_id}
        />
      )}
    </Card>
  );
}

// E2
export async function LinksCard({ searchParams }: Props) {
  const title = "Which links were clicked";
  const range = await rangeFrom(searchParams);
  const chosen = param(await searchParams, "campaign");
  const result = await attempt(async () => {
    const rows = await campaignsIn(range.start, range.end);
    const id = chosen ?? rows[0]?.campaign_id;
    if (!id) return { rows, links: null };
    const api = await apiClient();
    const response = await api.GET("/email/campaigns/{campaign_id}/links", {
      params: { path: { campaign_id: id } },
    });
    return {
      rows,
      links: response.response.status === 404 ? null : unwrap(response),
    };
  });
  if (!result) return <CardError title={title} />;
  const { rows, links } = result;
  const options = rows.map((r) => ({
    id: r.campaign_id,
    label: `${r.campaign_title}${r.send_time ? ` · ${ukDate(String(r.send_time))}` : ""}`,
  }));
  if (links && !options.some((o) => o.id === links.campaign_id)) {
    options.unshift({ id: links.campaign_id, label: links.campaign_title });
  }
  return (
    <Card
      title={title}
      subtitle={links ? links.campaign_title : undefined}
      action={
        links && options.length > 0 ? (
          <CampaignSelect campaigns={options} selected={links.campaign_id} />
        ) : undefined
      }
    >
      {!links ? (
        <p className="text-sm text-ink-2">
          {rows.length === 0
            ? "No campaigns sent in this period."
            : "That campaign wasn't found."}
        </p>
      ) : links.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No link clicks recorded.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {links.rows.map((link) => {
            const shown = link.url.replace(/^https?:\/\//, "");
            return (
              <li key={link.url} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    className="min-w-0 truncate text-accent hover:underline"
                    title={link.url}
                  >
                    {shown}
                  </a>
                  <span className="shrink-0 tabular-nums">
                    <span className="font-medium">
                      {count(link.total_clicks)}
                    </span>
                    <span className="ml-2 text-xs text-muted">
                      {link.share_of_clicks_pct === null
                        ? ""
                        : `${Math.round(link.share_of_clicks_pct)}%`}
                    </span>
                  </span>
                </div>
                <div
                  className="h-1.5 rounded-full bg-surface-sunken"
                  aria-hidden
                >
                  <div
                    className="h-full rounded-full bg-series-1"
                    style={{ width: `${link.share_of_clicks_pct ?? 0}%` }}
                  />
                </div>
                <p className="text-xs text-muted">
                  {count(link.unique_clicks)} people clicked
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

// E5
export async function SendTimesCard({ searchParams }: Props) {
  const title = "When people open and click";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/email/send-times", {
        params: { query: { start: range.start, end: range.end } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  return (
    <Card
      title={title}
      subtitle={`${count(result.campaigns)} campaign${result.campaigns === 1 ? "" : "s"} · ${range.label}`}
    >
      {result.campaigns === 0 ? (
        <p className="text-sm text-ink-2">No campaigns sent in this period.</p>
      ) : (
        <SendTiming
          afterSend={result.by_hours_after_send}
          ofDay={result.by_hour_of_day}
        />
      )}
    </Card>
  );
}

function growthInterval(days: number): "day" | "week" | "month" {
  if (days <= 31) return "day";
  return days <= 183 ? "week" : "month";
}

// E3
export async function GrowthCard({ searchParams }: Props) {
  const title = "Audience growth";
  const range = await rangeFrom(searchParams);
  const days = (Date.parse(range.end) - Date.parse(range.start)) / DAY + 1;
  const interval = growthInterval(days);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/email/audience-growth", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const data = result.data.map((row) => ({
    period: String(row.period),
    new_subscribers: row.new_subscribers ?? null,
    // Drawn below the line
    unsubscribes:
      row.unsubscribes === null || row.unsubscribes === undefined
        ? null
        : -Number(row.unsubscribes),
  }));
  const word = { day: "Daily", week: "Weekly", month: "Monthly" }[interval];
  const empty = data.every((r) => !r.new_subscribers && !r.unsubscribes);
  return (
    <Card
      title={title}
      subtitle={`${word} · ${range.label} · sign-ups through Mailchimp forms only`}
    >
      {empty ? (
        <p className="text-sm text-ink-2">
          No sign-ups or unsubscribes in this period.
        </p>
      ) : (
        <ChangeBars
          data={data}
          series={[
            {
              key: "new_subscribers",
              label: "New subscribers",
              colour: "var(--series-1)",
            },
            {
              key: "unsubscribes",
              label: "Unsubscribes",
              colour: "var(--series-2)",
            },
          ]}
          interval={interval}
          label={`New subscribers and unsubscribes per ${interval}`}
          signedValues={false}
        />
      )}
      <p className="text-xs text-muted">
        Contacts added by hand or imported don&apos;t show here; the subscriber
        total on the Overview includes them.
      </p>
    </Card>
  );
}

// E4
export async function ListHealthCard({ searchParams }: Props) {
  const title = "List health";
  const range = await rangeFrom(searchParams);
  const months = Math.min(
    36,
    Math.max(
      1,
      (Number(range.end.slice(0, 4)) - Number(range.start.slice(0, 4))) * 12 +
        Number(range.end.slice(5, 7)) -
        Number(range.start.slice(5, 7)) +
        1,
    ),
  );
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/email/list-health", { params: { query: { months } } }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const noLosses = result.data.every(
    (row) => !row.unsubscribed && !row.cleaned && !row.bounces,
  );
  const measures = [
    { key: "unsubscribed", title: "Unsubscribed" },
    { key: "cleaned", title: "Cleaned (dead addresses)" },
    { key: "bounces", title: "Bounces (per send)" },
  ];
  return (
    <Card
      title={title}
      subtitle={`What the list loses each month · last ${months} month${months === 1 ? "" : "s"} · each chart has its own scale`}
    >
      {noLosses ? (
        <p className="text-sm text-ink-2">
          No unsubscribes, cleaned addresses or bounces recorded in this period.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          {measures.map((m) => (
            <MiniBars
              key={m.key}
              title={m.title}
              data={result.data.map((row) => ({
                period: String(row.period),
                value:
                  row[m.key] === null || row[m.key] === undefined
                    ? null
                    : Number(row[m.key]),
              }))}
            />
          ))}
        </div>
      )}
      <p className="text-xs text-muted">
        Bounces are emails that couldn&apos;t be delivered, counted per send:
        hard bounces (the address doesn&apos;t exist) and soft bounces (a
        temporary problem, like a full inbox). Mailchimp &quot;cleans&quot; an
        address, removing it from the list, after a hard bounce or repeated soft
        bounces. Rising bounces can mean a deliverability problem.
      </p>
    </Card>
  );
}
