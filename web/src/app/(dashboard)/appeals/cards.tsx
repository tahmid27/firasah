import { Card, CardError, attempt } from "@/components/card";
import { Delta } from "@/components/delta";
import { apiClient, unwrap } from "@/lib/api";
import { count, gbp, percent, signed, ukDate } from "@/lib/format";
import { rangeFrom, type SearchParams } from "@/lib/range-server";

import { Timeline, type Period } from "./client";

type Props = { searchParams: SearchParams };
const DAY = 86_400_000;

function ukDay(timestamp: string) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(
    new Date(timestamp),
  );
}

function mondayOf(isoDate: string) {
  const d = new Date(`${isoDate}T00:00:00Z`);
  const back = (d.getUTCDay() + 6) % 7;
  return new Date(d.getTime() - back * DAY).toISOString().slice(0, 10);
}

// A2
export async function WindowCard({ searchParams }: Props) {
  const title = "This period against the one before";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/appeals/window-report", {
        params: { query: { start: range.start, end: range.end } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const { current: now, previous: before } = result;
  const pct = (a: number, b: number) => (b ? ((a - b) / b) * 100 : null);
  const rows = [
    {
      label: "Raised",
      now: gbp(now.raised),
      before: gbp(before.raised),
      change: pct(now.raised, before.raised),
    },
    {
      label: "Donations",
      now: count(now.donations),
      before: count(before.donations),
      change: pct(now.donations, before.donations),
    },
    {
      label: "Posts",
      now: count(now.posts),
      before: count(before.posts),
      change: pct(now.posts, before.posts),
    },
    {
      label: "Emails sent",
      now: count(now.emails),
      before: count(before.emails),
      change: pct(now.emails, before.emails),
    },
    {
      label: "Follower change",
      now: now.follower_change === null ? "–" : signed(now.follower_change),
      before:
        before.follower_change === null ? "–" : signed(before.follower_change),
      change: null,
    },
  ];
  return (
    <Card
      title={title}
      subtitle={`${range.label} against ${ukDate(String(before.start))} – ${ukDate(String(before.end))}`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-muted">
              <th className="py-2 pr-3 font-normal" />
              <th className="py-2 pr-3 text-right font-normal">This period</th>
              <th className="py-2 pr-3 text-right font-normal">
                Period before
              </th>
              <th className="py-2 text-right font-normal">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.label}
                className="border-b border-hairline last:border-0"
              >
                <td className="py-2 pr-3 text-ink-2">{row.label}</td>
                <td className="py-2 pr-3 text-right font-medium tabular-nums">
                  {row.now}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                  {row.before}
                </td>
                <td className="py-2 text-right">
                  {row.change === null ? (
                    <span className="text-xs text-muted">–</span>
                  ) : (
                    <span className="inline-flex justify-end">
                      <Delta pct={row.change} label="" />
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// A1
export async function TimelineCard({ searchParams }: Props) {
  const title = "Donations, posts and emails";
  const range = await rangeFrom(searchParams);
  const days = (Date.parse(range.end) - Date.parse(range.start)) / DAY + 1;
  const interval = days <= 120 ? "day" : "week";
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/appeals/timeline", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const bucket = (timestamp: string) =>
    interval === "day" ? ukDay(timestamp) : mondayOf(ukDay(timestamp));
  const byPeriod = new Map<string, Period>(
    result.donations.data.map((row) => {
      const period = String(row.period);
      return [
        period,
        { period, raised: Number(row.raised ?? 0), emails: [], posts: 0 },
      ];
    }),
  );
  for (const event of result.events) {
    const p = byPeriod.get(bucket(String(event.at)));
    if (!p) continue;
    if (event.kind === "email") p.emails.push(event.title ?? "Untitled email");
    else p.posts += 1;
  }
  const emails = result.events.filter((e) => e.kind === "email").length;
  const posts = result.events.length - emails;
  const nothing =
    result.events.length === 0 &&
    [...byPeriod.values()].every((p) => p.raised === 0);
  return (
    <Card
      title={title}
      subtitle={`${interval === "day" ? "Daily" : "Weekly"} · ${range.label} · ${count(emails)} emails, ${count(posts)} posts`}
    >
      {nothing ? (
        <p className="text-sm text-ink-2">
          No donations, posts or emails in this period.
        </p>
      ) : (
        <Timeline data={[...byPeriod.values()]} interval={interval} />
      )}
      <p className="text-xs text-muted">
        Shows what went out around a rise in giving, not that it caused it:
        appeals, paydays and seasons like Ramadan move giving too.
      </p>
    </Card>
  );
}

// A3
export async function EmailLiftCard({ searchParams }: Props) {
  const title = "Giving around each email";
  const range = await rangeFrom(searchParams);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/appeals/email-lift", {
        params: { query: { start: range.start, end: range.end, limit: 50 } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  return (
    <Card
      title={title}
      subtitle={`Donations on the day of each email and the day after, against a typical two days in the ${result.baseline_days} days before`}
    >
      {result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No emails sent in this period.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hairline text-left text-xs text-muted">
                <th className="py-2 pr-3 font-normal">Email</th>
                <th className="py-2 pr-3 text-right font-normal">
                  Raised in 2 days
                </th>
                <th className="hidden py-2 pr-3 text-right font-normal sm:table-cell">
                  Typical 2 days
                </th>
                <th className="py-2 text-right font-normal">Difference</th>
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row) => (
                <tr
                  key={row.campaign_id}
                  className="border-b border-hairline align-top last:border-0"
                >
                  <td className="py-2 pr-3">
                    <p className="font-medium">{row.campaign_title}</p>
                    <p className="text-xs text-muted">
                      {ukDate(String(row.send_time))} ·{" "}
                      {count(row.donations_2_days)} donations
                    </p>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {gbp(row.raised_2_days)}
                  </td>
                  <td className="hidden py-2 pr-3 text-right tabular-nums text-ink-2 sm:table-cell">
                    {row.typical_2_days === null
                      ? "–"
                      : gbp(row.typical_2_days)}
                  </td>
                  <td className="py-2 text-right tabular-nums">
                    {row.lift_pct === null
                      ? "–"
                      : `${row.lift_pct > 0 ? "+" : row.lift_pct < 0 ? "−" : ""}${percent(row.lift_pct, 0)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted">
        A pattern to look at, not proof: other things happen on the same days.
        One big donation can make a single email look like it worked.
      </p>
    </Card>
  );
}
