import { Card, CardError, attempt } from "@/components/card";
import { ChangeBars } from "@/components/charts/change-bars";
import { Heatmap } from "@/components/charts/heatmap";
import { LineSeries } from "@/components/charts/line-series";
import { StackedBars } from "@/components/charts/stacked-bars";
import { Delta } from "@/components/delta";
import { PlatformFilter } from "@/components/platform-filter";
import { apiClient, connectedSources, unwrap } from "@/lib/api";
import { count, percent, rate, signed } from "@/lib/format";
import { PLATFORM_COLOURS, platformName } from "@/lib/platforms";
import { SORTS, type Sort } from "@/lib/post-sorts";
import { param, rangeFrom, type SearchParams } from "@/lib/range-server";

import { ActivityChart, PostsTable, SortSelect } from "./client";

type Props = { searchParams: SearchParams };
type Platform = "instagram" | "tiktok";
const SOCIAL: Platform[] = ["instagram", "tiktok"];
const DAY = 86_400_000;

async function context(searchParams: SearchParams) {
  const range = await rangeFrom(searchParams);
  const raw = param(await searchParams, "platform");
  const platform = SOCIAL.includes(raw as Platform)
    ? (raw as Platform)
    : undefined;
  const days = (Date.parse(range.end) - Date.parse(range.start)) / DAY + 1;
  return { range, platform, days };
}

// Daily up to four months, weekly up to two years, monthly beyond.
function trendInterval(days: number): "day" | "week" | "month" {
  if (days <= 120) return "day";
  return days <= 730 ? "week" : "month";
}

// Net change per period: daily up to a month, weekly up to six months.
function changeInterval(days: number): "day" | "week" | "month" {
  if (days <= 31) return "day";
  return days <= 183 ? "week" : "month";
}

function seriesFor(
  keys: { key: string; label: string }[],
  platform?: Platform,
) {
  return keys
    .filter((s) => !platform || s.key === platform)
    .map((s) => ({
      key: s.key,
      label: s.label,
      colour: PLATFORM_COLOURS[s.key] ?? "var(--series-3)",
    }));
}

export async function SocialPlatformControl() {
  const connected = await attempt(connectedSources);
  const platforms = SOCIAL.filter((p) => connected?.has(p));
  return platforms.length > 1 ? <PlatformFilter platforms={platforms} /> : null;
}

// Followers now and change over the range, posts published, average engagement
export async function SocialTotals({ searchParams }: Props) {
  const { range, platform, days } = await context(searchParams);
  const result = await attempt(async () => {
    const client = await apiClient();
    const [followers, formats] = await Promise.all([
      client.GET("/social/followers-over-time", {
        params: {
          query: {
            start: range.start,
            end: range.end,
            interval: trendInterval(days),
          },
        },
      }),
      client.GET("/social/formats", {
        params: { query: { start: range.start, end: range.end, platform } },
      }),
    ]);
    return { followers: unwrap(followers), formats: unwrap(formats) };
  });
  if (!result) {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        <CardError title="Followers" />
      </div>
    );
  }
  const keys = seriesFor(result.followers.series, platform).map((s) => s.key);
  const firstLast = (key: string) => {
    const known = result.followers.data
      .map((row) => row[key])
      .filter((v): v is number => typeof v === "number");
    return known.length ? [known[0], known[known.length - 1]] : null;
  };
  const ends = keys.map(firstLast);
  const complete = ends.every(Boolean) && ends.length > 0;
  const start = complete ? ends.reduce((s, e) => s + e![0], 0) : null;
  const end = complete ? ends.reduce((s, e) => s + e![1], 0) : null;
  const posts = result.formats.rows.reduce((s, r) => s + r.posts, 0);
  const weighted = result.formats.rows.filter(
    (r) => r.average_engagement_rate !== null,
  );
  const weight = weighted.reduce((s, r) => s + r.posts, 0);
  const engagement = weight
    ? weighted.reduce((s, r) => s + r.average_engagement_rate! * r.posts, 0) /
      weight
    : null;
  const which = platform ? platformName(platform) : "All platforms";

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card
        title="Followers"
        subtitle={`${which} · at ${range.label.split(" – ").pop()}`}
      >
        {end === null ? (
          <p className="text-sm text-ink-2">
            No follower readings in this period.
          </p>
        ) : (
          <div>
            <p className="text-3xl font-semibold tracking-tight">
              {count(end)}
            </p>
            <Delta
              pct={start ? ((end - start) / start) * 100 : null}
              label={`${signed(end - start!)} in this period`}
            />
          </div>
        )}
      </Card>
      <Card title="Posts published" subtitle={`${which} · ${range.label}`}>
        <p className="text-3xl font-semibold tracking-tight">{count(posts)}</p>
        <p className="text-xs text-muted">
          About {(posts / Math.max(1, days / 7)).toFixed(1)} a week
        </p>
      </Card>
      <Card
        title="Average engagement"
        subtitle={`${which} · posts in ${range.label}`}
      >
        <p className="text-3xl font-semibold tracking-tight">
          {engagement === null ? "–" : rate(engagement)}
        </p>
        <p className="text-xs text-muted">
          Likes, comments, shares and saves per person who saw the post
        </p>
      </Card>
    </div>
  );
}

// S1
export async function FollowersCard({ searchParams }: Props) {
  const title = "Followers over time";
  const { range, platform, days } = await context(searchParams);
  const interval = trendInterval(days);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/followers-over-time", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const series = seriesFor(result.series, platform);
  return (
    <Card title={title} subtitle={`${range.label} · each platform separately`}>
      {series.length === 0 ? (
        <p className="text-sm text-ink-2">
          No follower readings in this period.
        </p>
      ) : (
        <LineSeries
          data={result.data.map((row) => ({
            ...row,
            period: String(row.period),
          }))}
          series={series}
          interval={interval}
          label={`Followers over time, ${range.label}`}
        />
      )}
    </Card>
  );
}

// S2
export async function NetFollowersCard({ searchParams }: Props) {
  const title = "Followers gained or lost";
  const { range, platform, days } = await context(searchParams);
  const interval = changeInterval(days);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/net-followers", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const series = seriesFor(result.series, platform);
  const word = { day: "Daily", week: "Weekly", month: "Monthly" }[interval];
  return (
    <Card title={title} subtitle={`${word} · ${range.label} · after unfollows`}>
      {series.length === 0 ? (
        <p className="text-sm text-ink-2">
          No follower readings in this period.
        </p>
      ) : (
        <ChangeBars
          data={result.data.map((row) => ({
            ...row,
            period: String(row.period),
          }))}
          series={series}
          interval={interval}
          label={`Net followers per ${interval}, ${range.label}`}
        />
      )}
    </Card>
  );
}

// S3
export async function PostsCard({ searchParams }: Props) {
  const title = "Posts";
  const { range, platform } = await context(searchParams);
  const raw = param(await searchParams, "sort");
  const sort: Sort = raw && raw in SORTS ? (raw as Sort) : "engagement_rate";
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/posts", {
        params: {
          query: {
            start: range.start,
            end: range.end,
            platform,
            sort,
            limit: 50,
          },
        },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  return (
    <Card
      title={title}
      subtitle={`Published ${range.label}${platform ? ` · ${platformName(platform)}` : ""}`}
      action={<SortSelect selected={sort} />}
    >
      {result.rows.length === 0 ? (
        <p className="text-sm text-ink-2">No posts in this period.</p>
      ) : (
        <>
          <PostsTable
            key={`${sort}|${platform}|${range.start}|${range.end}`}
            rows={result.rows.map((r) => ({
              ...r,
              posted_at: String(r.posted_at),
            }))}
          />
          <p className="text-xs text-muted">
            Engagement: {result.engagement_basis}
          </p>
        </>
      )}
    </Card>
  );
}

// S4
export async function FormatsCard({ searchParams }: Props) {
  const title = "What format works best";
  const { range, platform } = await context(searchParams);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/formats", {
        params: { query: { start: range.start, end: range.end, platform } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const rows = result.rows
    .filter((r) => r.median_engagement_rate !== null)
    .sort((a, b) => b.median_engagement_rate! - a.median_engagement_rate!);
  const top = rows[0]?.median_engagement_rate ?? 0;
  const many = new Set(rows.map((r) => r.platform)).size > 1;
  return (
    <Card
      title={title}
      subtitle={`Typical (median) engagement per post · ${range.label}`}
    >
      {rows.length === 0 ? (
        <p className="text-sm text-ink-2">
          No posts with engagement data in this period.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.map((row) => (
            <li
              key={`${row.platform}-${row.format}`}
              className="flex flex-col gap-1"
            >
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span>
                  <span className="font-medium">{row.format}</span>
                  {many && row.format !== "TikTok video" && (
                    <span className="ml-2 text-xs text-muted">
                      {platformName(row.platform)}
                    </span>
                  )}
                  <span className="ml-2 text-xs text-muted">
                    {count(row.posts)} post{row.posts === 1 ? "" : "s"}
                  </span>
                </span>
                <span className="font-medium tabular-nums">
                  {rate(row.median_engagement_rate!)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-sunken" aria-hidden>
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${top ? (row.median_engagement_rate! / top) * 100 : 0}%`,
                    background: PLATFORM_COLOURS[row.platform],
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
      {rows.some((r) => r.posts < 5) && (
        <p className="text-xs text-muted">
          Formats with only a few posts can swing a lot. Treat them as a hint.
        </p>
      )}
    </Card>
  );
}

// S5
export async function ConsistencyCard({ searchParams }: Props) {
  const title = "Posting consistency";
  const { platform, days } = await context(searchParams);
  const weeks = Math.min(104, Math.max(1, Math.ceil(days / 7)));
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/posting-consistency", {
        params: { query: { weeks } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const series = seriesFor(result.posts_per_week.series, platform);
  const last = result.last_posts.filter(
    (p) => !platform || p.platform === platform,
  );
  return (
    <Card title={title} subtitle={`Posts per week · last ${weeks} weeks`}>
      <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {last.map((p) => (
          <li key={p.platform}>
            <span className="text-muted">{platformName(p.platform)}: </span>
            <span className="font-medium">
              {p.days_since === 0
                ? "posted today"
                : p.days_since === 1
                  ? "last post yesterday"
                  : `last post ${p.days_since} days ago`}
            </span>
          </li>
        ))}
      </ul>
      {series.length > 0 && (
        <StackedBars
          data={result.posts_per_week.data.map((row) => ({
            ...row,
            period: String(row.period),
            partial: false,
          }))}
          series={series}
          interval="week"
          label={`Posts per week, last ${weeks} weeks`}
          unit="count"
        />
      )}
    </Card>
  );
}

// S6
export async function BestTimeCard({ searchParams }: Props) {
  const title = "Best time to post";
  const { range, platform } = await context(searchParams);
  const result = await attempt(async () =>
    unwrap(
      await (
        await apiClient()
      ).GET("/social/best-time", {
        params: { query: { start: range.start, end: range.end, platform } },
      }),
    ),
  );
  if (!result) return <CardError title={title} />;
  const posts = result.cells.reduce((s, c) => s + c.count, 0);
  return (
    <Card
      title={title}
      subtitle={`When posts were published, UK time · ${range.label}`}
    >
      <Heatmap cells={result.cells} kind="posts" />
      {posts < 50 && posts > 0 && (
        <p className="text-xs text-muted">
          Only {count(posts)} posts in this period, so single slots can mislead.
          A longer range gives a steadier picture.
        </p>
      )}
    </Card>
  );
}

const ACTIVITY_SERIES = [
  { key: "reach", label: "Reach" },
  { key: "views", label: "Views" },
  { key: "accounts_engaged", label: "Accounts engaged" },
  { key: "interactions", label: "Interactions" },
  { key: "link_taps", label: "Profile link taps" },
];

// S7
export async function InstagramActivityCard({ searchParams }: Props) {
  const title = "Instagram account activity";
  const { range, platform, days } = await context(searchParams);
  const interval = trendInterval(days);
  const result = await attempt(async () => {
    const [activity, connected] = await Promise.all([
      (await apiClient()).GET("/social/account-daily", {
        params: { query: { start: range.start, end: range.end, interval } },
      }),
      connectedSources(),
    ]);
    return { activity: unwrap(activity), connected };
  });
  if (!result) return <CardError title={title} />;
  return (
    <Card
      title={title}
      subtitle={`Whole account, not just new posts · ${range.label}`}
    >
      {platform === "tiktok" ? (
        <p className="text-sm text-ink-2">
          TikTok&apos;s API doesn&apos;t give account-level daily activity. This
          card is Instagram only.
        </p>
      ) : !result.connected.has("instagram") ? (
        <p className="text-sm text-ink-2">Instagram isn&apos;t connected.</p>
      ) : (
        <ActivityChart
          data={result.activity.data.map((row) => ({
            ...row,
            period: String(row.period),
          }))}
          series={ACTIVITY_SERIES}
          interval={interval}
        />
      )}
    </Card>
  );
}

const regions = new Intl.DisplayNames(["en-GB"], { type: "region" });
const GENDERS: Record<string, string> = {
  F: "Women",
  M: "Men",
  U: "Not specified",
};

function Breakdown({
  title,
  items,
  label = (v: string) => v,
}: {
  title: string;
  items: { value: string; followers: number; share_pct: number }[];
  label?: (value: string) => string;
}) {
  const top = Math.max(...items.map((i) => i.share_pct), 1);
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-medium text-ink-2">{title}</h3>
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li key={item.value} className="flex flex-col gap-0.5">
            <div className="flex justify-between gap-3 text-sm">
              <span className="truncate">{label(item.value)}</span>
              <span className="tabular-nums text-ink-2">
                {percent(item.share_pct, 0)}
              </span>
            </div>
            <div className="h-1 rounded-full bg-surface-sunken" aria-hidden>
              <div
                className="h-full rounded-full bg-series-1"
                style={{ width: `${(item.share_pct / top) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// S8
export async function DemographicsCard() {
  const title = "Who your Instagram followers are";
  const result = await attempt(async () => {
    const [demographics, connected] = await Promise.all([
      (await apiClient()).GET("/social/demographics"),
      connectedSources(),
    ]);
    return { demographics: unwrap(demographics), connected };
  });
  if (!result) return <CardError title={title} />;
  const { breakdowns, as_of } = result.demographics;
  const classified = (breakdowns.gender ?? []).reduce(
    (s, b) => s + b.followers,
    0,
  );
  const country = (code: string) => {
    try {
      return regions.of(code) ?? code;
    } catch {
      return code;
    }
  };
  const ages = [...(breakdowns.age ?? [])].sort((a, b) =>
    a.value.localeCompare(b.value),
  );
  return (
    <Card
      title={title}
      subtitle={
        as_of
          ? `Latest snapshot · based on the ${count(classified)} followers Instagram could classify, shown as shares`
          : undefined
      }
    >
      {!result.connected.has("instagram") || !as_of ? (
        <p className="text-sm text-ink-2">No follower demographics yet.</p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Breakdown title="Age" items={ages} />
          <Breakdown
            title="Gender"
            items={breakdowns.gender ?? []}
            label={(v) => GENDERS[v] ?? v}
          />
          <Breakdown
            title="Top countries"
            items={(breakdowns.country ?? []).slice(0, 6)}
            label={country}
          />
          <Breakdown
            title="Top cities"
            items={(breakdowns.city ?? []).slice(0, 6)}
          />
        </div>
      )}
    </Card>
  );
}
