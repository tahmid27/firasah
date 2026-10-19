import { ExternalLink } from "lucide-react";
import Link from "next/link";

import { Card, CardError, attempt } from "@/components/card";
import { MonthlyBars } from "@/components/charts/monthly-bars";
import { Delta } from "@/components/delta";
import { HealthBadge } from "@/components/health-badge";
import {
  apiClient,
  getFundraisingSummary,
  getOverviewSummary,
  unwrap,
} from "@/lib/api";
import {
  ago,
  count,
  dayMonth,
  gbp,
  gbpExact,
  monthYear,
  rate,
  signed,
  ukDate,
} from "@/lib/format";
import { healthOf } from "@/lib/source-status";

// O1
export async function RaisedTile() {
  const title = "Raised this month";
  const summary = await attempt(getFundraisingSummary);
  if (!summary) return <CardError title={title} />;

  const { this_month: now, last_month_to_date: before } = summary;
  return (
    <Card
      title={title}
      subtitle={`${monthYear(now.month_start)}, up to ${dayMonth(now.through)}`}
    >
      <div>
        <p className="text-3xl font-semibold tracking-tight">
          {gbp(now.raised)}
        </p>
        <Delta
          pct={summary.raised_change_pct}
          label={`vs ${gbp(before.raised)} by ${dayMonth(before.through)}`}
        />
      </div>
      <dl className="grid grid-cols-2 gap-3 border-t border-hairline pt-3 text-sm">
        <div>
          <dt className="text-xs text-muted">Donations</dt>
          <dd className="font-medium tabular-nums">{count(now.donations)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Average gift</dt>
          <dd className="font-medium tabular-nums">
            {now.average_gift === null ? "–" : gbpExact(now.average_gift)}
          </dd>
        </div>
      </dl>
      {summary.excluded_non_gbp_donations > 0 && (
        <p className="text-xs text-muted">
          GBP only: {count(summary.excluded_non_gbp_donations)} donation
          {summary.excluded_non_gbp_donations === 1 ? "" : "s"} in other
          currencies not included.
        </p>
      )}
    </Card>
  );
}

// O2, O3
export async function AudienceTile({
  metric,
}: {
  metric: "followers" | "email_subscribers";
}) {
  const title =
    metric === "followers" ? "Social followers" : "Email subscribers";
  const subtitle =
    metric === "followers"
      ? "Total across your social accounts"
      : "Subscribed to your list";
  const summary = await attempt(getOverviewSummary);
  if (!summary) return <CardError title={title} />;

  const m = summary[metric];
  return (
    <Card title={title} subtitle={subtitle}>
      {m.value === null ? (
        <p className="text-sm text-ink-2">No data yet.</p>
      ) : (
        <div>
          <p className="text-3xl font-semibold tracking-tight">
            {count(m.value)}
          </p>
          <Delta
            pct={m.change_pct}
            label={
              m.change === null
                ? "30 days of history needed"
                : `${signed(m.change)} since ${dayMonth(summary.compared_with)}`
            }
          />
        </div>
      )}
    </Card>
  );
}

// O4
export async function IncomeCard() {
  const title = "Income, last 12 months";
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(await api.GET("/fundraising/income-over-time"));
  });
  if (!result) return <CardError title={title} />;

  const keys = result.series.map((s) => s.key);
  const data = result.data.map((row, index) => ({
    period: String(row.period),
    value: keys.reduce((sum, key) => sum + Number(row[key] ?? 0), 0),
    partial: index === result.data.length - 1,
  }));
  const labels = result.series.map((s) => s.label);
  const source =
    labels.length > 1 ? `${labels.join(" and ")} combined` : `From ${labels[0]}`;
  return (
    <Card
      title={title}
      subtitle={
        labels.length
          ? `${source} · this month so far shown lighter`
          : undefined
      }
      action={<SeeMore href="/fundraising" />}
    >
      {keys.length === 0 ? (
        <p className="text-sm text-ink-2">
          No donations in the last 12 months.
        </p>
      ) : (
        <MonthlyBars
          data={data}
          label={`Monthly income for the last 12 months`}
        />
      )}
    </Card>
  );
}

// O5
export async function DataHealthCard() {
  const title = "Data health";
  const result = await attempt(async () => {
    const api = await apiClient();
    return unwrap(await api.GET("/data-health/sources"));
  });
  if (!result) return <CardError title={title} />;

  return (
    <Card title={title} action={<SeeMore href="/data-health" />}>
      <ul className="flex flex-col divide-y divide-hairline">
        {result.sources.map((source) => {
          const state = healthOf(source);
          return (
            <li
              key={source.source}
              className="flex items-center justify-between gap-3 py-2"
            >
              <div>
                <p className="text-sm font-medium">{source.label}</p>
                {source.hours_since_data !== null && (
                  <p className="text-xs text-muted">
                    Latest data {ago(source.hours_since_data)}
                  </p>
                )}
              </div>
              <HealthBadge state={state} />
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// O6
export async function TopFundraisersCard() {
  const title = "Top fundraisers this month";
  const result = await attempt(async () => {
    const summary = await getFundraisingSummary();
    const api = await apiClient();
    return unwrap(
      await api.GET("/fundraising/fundraisers", {
        params: {
          query: {
            start: summary.this_month.month_start,
            end: summary.this_month.through,
            limit: 5,
          },
        },
      }),
    );
  });
  if (!result) return <CardError title={title} />;

  const top = result.rows[0]?.raised ?? 0;
  return (
    <Card title={title} action={<SeeMore href="/fundraising" />}>
      {result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No donations yet this month.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {result.rows.map((row, index) => (
            <li
              key={`${row.source}-${row.fundraiser_name}`}
              className="flex flex-col gap-1"
            >
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0">
                  <span className="mr-2 text-muted tabular-nums">
                    {index + 1}
                  </span>
                  <span className="font-medium">{row.fundraiser_name}</span>
                  {row.project_name && (
                    <span className="block truncate pl-5 text-xs text-muted">
                      {row.project_name}
                    </span>
                  )}
                </span>
                <span className="shrink-0 font-medium tabular-nums">
                  {gbp(row.raised)}
                </span>
              </div>
              <div
                className="ml-5 h-1.5 rounded-full bg-surface-sunken"
                aria-hidden
              >
                <div
                  className="h-full rounded-full bg-series-1"
                  style={{ width: `${top ? (row.raised / top) * 100 : 0}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

// O7
export async function LatestActivityCard() {
  const title = "Latest post and email";
  const result = await attempt(async () => {
    const api = await apiClient();
    const [posts, campaigns] = await Promise.all([
      api.GET("/social/posts", {
        params: { query: { sort: "posted_at", limit: 1 } },
      }),
      api.GET("/email/campaigns", { params: { query: { limit: 1 } } }),
    ]);
    return { post: unwrap(posts).rows[0], email: unwrap(campaigns).rows[0] };
  });
  if (!result) return <CardError title={title} />;
  const { post, email } = result;

  return (
    <Card title={title}>
      <div className="grid gap-4 sm:grid-cols-2">
        <article className="flex flex-col gap-2 rounded-md bg-surface-sunken p-3">
          <p className="text-xs text-muted">
            Latest post
            {post &&
              ` · ${platformName(post.platform)} ${post.format.toLowerCase()} · ${ukDate(post.posted_at)}`}
          </p>
          {post ? (
            <>
              <p className="line-clamp-3 text-sm">
                {post.caption || "No caption"}
              </p>
              <p className="mt-auto text-xs text-ink-2 tabular-nums">
                {[
                  post.reach !== null && `${count(post.reach)} reached`,
                  post.views !== null && `${count(post.views)} views`,
                  post.likes !== null && `${count(post.likes)} likes`,
                  post.engagement_rate !== null &&
                    `${rate(post.engagement_rate)} engagement`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {post.permalink && (
                <a
                  href={post.permalink}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
                >
                  Open post <ExternalLink size={12} aria-hidden />
                </a>
              )}
            </>
          ) : (
            <p className="text-sm text-ink-2">No posts yet.</p>
          )}
        </article>
        <article className="flex flex-col gap-2 rounded-md bg-surface-sunken p-3">
          <p className="text-xs text-muted">
            Latest email{email?.send_time && ` · ${ukDate(email.send_time)}`}
          </p>
          {email ? (
            <>
              <p className="text-sm font-medium">{email.campaign_title}</p>
              {email.subject_line && (
                <p className="line-clamp-2 text-sm text-ink-2">
                  {email.subject_line}
                </p>
              )}
              <p className="mt-auto text-xs text-ink-2 tabular-nums">
                {[
                  `${count(email.emails_sent)} sent`,
                  email.open_rate !== null && `${rate(email.open_rate)} opened`,
                  email.click_rate !== null &&
                    `${rate(email.click_rate)} clicked`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <Link
                href="/email"
                className="text-xs text-accent hover:underline"
              >
                All campaigns
              </Link>
            </>
          ) : (
            <p className="text-sm text-ink-2">No emails sent yet.</p>
          )}
        </article>
      </div>
    </Card>
  );
}

function SeeMore({ href }: { href: string }) {
  return (
    <Link href={href} className="shrink-0 text-xs text-accent hover:underline">
      View more
    </Link>
  );
}

function platformName(platform: string) {
  return platform === "tiktok"
    ? "TikTok"
    : platform === "instagram"
      ? "Instagram"
      : platform;
}
