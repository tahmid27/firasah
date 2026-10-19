"""Instagram and TikTok responses: account history, posts, insights,
demographics, plus raw-only tables for data we can't pull yet (Instagram
stories, TikTok profile fields and Business API metrics)."""

import math
import random
from datetime import UTC, date, datetime, time, timedelta

from ingestion.instagram_posts import (
    shape_account_day,
    shape_demographics,
    shape_media_insights,
)
from synthetic.batches import Batch
from synthetic.charities import Charity
from synthetic.marketing import Post
from synthetic.rand import audience_series, rng

AGES = ("13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+")


def _pull_time(day: date) -> datetime:
    return datetime.combine(day, time(6, 0), tzinfo=UTC)


def follower_series(
    r: random.Random, start: date, end: date, counts: tuple[int, int], posts: list[Post]
) -> dict[date, int]:
    """Uneven growth with a jump after the rare post that took off, small
    unfollow dips after a run of quiet days, and the occasional purge of
    inactive accounts by the platform."""
    bumps = {p.posted_at.date(): p.effect * 6 for p in posts if p.effect > 0.2}
    drops: dict[date, float] = {}
    day = start + timedelta(days=r.randint(30, 120))
    while day <= end:
        drops[day] = r.uniform(0.003, 0.012)  # platform purge
        day += timedelta(days=r.randint(60, 150))
    for i in range((end - start).days):
        if r.random() < 0.04:
            day = start + timedelta(days=i)
            drops[day] = drops.get(day, 0.0) + r.uniform(0.0005, 0.002)
    return audience_series(r, start, end, counts, bumps, drops)


def _post_metrics(r: random.Random, p: Post, followers: int, now: datetime) -> dict:
    """Lifetime counts and Instagram-insights-style metrics for one post."""
    factor = {
        "REELS": (0.7, 0.8),
        "CAROUSEL_ALBUM": (0.25, 0.45),
        "IMAGE": (0.18, 0.45),
    }.get(p.product_type if p.product_type == "REELS" else p.media_type, (0.8, 1.2))
    reach = max(
        5,
        round(
            followers
            * r.lognormvariate(math.log(factor[0]), factor[1])
            * (1 + 3 * p.effect)
        ),
    )
    likes = max(0, round(reach * r.lognormvariate(math.log(0.06), 0.4)))
    age = now - p.posted_at
    is_video = p.media_type == "VIDEO"
    views = (
        round(reach * r.uniform(1.2, 2.0))
        if is_video
        else (round(reach * r.uniform(1.1, 1.6)) if age < timedelta(days=365) else 0)
    )
    metrics = {
        "likes": likes,
        "comments": round(likes * r.uniform(0.02, 0.08)),
        "shares": round(likes * r.uniform(0.02, 0.12)),
        "saved": round(likes * r.uniform(0.03, 0.15)),
        "reach": reach,
        "views": views,
    }
    if age > timedelta(days=730):
        # Instagram keeps insights for two years: old posts keep lifetime
        # likes but report only a sliver of reach
        metrics.update(reach=r.randint(2, 30), views=0, shares=0, saved=r.randint(0, 3))
    return metrics


def _insights_payload(r: random.Random, p: Post, m: dict) -> dict:
    values = {
        "reach": m["reach"],
        "views": m["views"],
        "shares": m["shares"],
        "saved": m["saved"],
        "total_interactions": m["likes"] + m["comments"] + m["shares"] + m["saved"],
        "reposts": round(m["shares"] * r.uniform(0, 0.2)),
    }
    if p.product_type == "REELS":
        average_ms = r.randint(6_000, 18_000)
        values |= {
            "ig_reels_avg_watch_time": average_ms,
            "ig_reels_video_view_total_time": average_ms * max(m["views"], 1),
            "reels_skip_rate": round(r.uniform(20, 55), 1),
        }
    else:
        values |= {
            "profile_visits": round(m["reach"] * r.uniform(0.005, 0.02)),
            "follows": round(m["reach"] * r.uniform(0.0005, 0.004)),
        }
    return {
        "data": [
            {"name": k, "period": "lifetime", "values": [{"value": v}]}
            for k, v in values.items()
        ]
    }


def _demographics_payloads(
    r: random.Random, charity: Charity, followers: int, drift: float
) -> dict[str, dict]:
    covered = followers * 0.25  # platforms only classify some followers
    muslim = charity.muslim_donor_share
    shares = {
        "age": dict(
            zip(
                AGES,
                (0.02, 0.18 + 0.05 * muslim, 0.36, 0.22, 0.12, 0.07, 0.03),
                strict=True,
            )
        ),
        "gender": {"F": 0.52 + 0.04 * drift, "M": 0.40 - 0.04 * drift, "U": 0.08},
        "country": {
            "GB": 0.82,
            "US": 0.04,
            "PK": 0.04 * muslim + 0.01,
            "IN": 0.02,
            "IE": 0.02,
            "BD": 0.03 * muslim + 0.01,
        },
        "city": {
            f"{city}, England" if city not in ("Cardiff", "Glasgow") else city: w
            for city, w in zip(
                charity.cities,
                (0.3, 0.15, 0.12, 0.1, 0.08, 0.06, 0.05, 0.04),
                strict=False,
            )
        },
    }
    payloads = {}
    for breakdown, weights in shares.items():
        results = [
            {
                "dimension_values": [value],
                "value": max(1, round(covered * w * r.uniform(0.9, 1.1))),
            }
            for value, w in weights.items()
        ]
        payloads[breakdown] = {
            "data": [
                {
                    "name": "follower_demographics",
                    "period": "lifetime",
                    "total_value": {
                        "breakdowns": [
                            {"dimension_keys": [breakdown], "results": results}
                        ]
                    },
                }
            ]
        }
    return payloads


def instagram_batches(
    charity: Charity, posts: list[Post], start: date, end: date, seed: int
) -> list[Batch]:
    r = rng(seed, charity.org_id, "instagram-format")
    ig_user_id = str(17_841_400_000_000_000 + r.randint(0, 99_999_999))
    tags = {"_ig_user_id": ig_user_id}
    now = _pull_time(end)
    followers = follower_series(r, start, end, charity.followers["instagram"], posts)

    info_rows, info_times = [], []
    for day, count in followers.items():
        info_rows.append(
            {
                "id": ig_user_id,
                "username": charity.handle,
                "name": charity.name,
                "biography": f"{charity.name} · {charity.city}-based charity · Donate via the link below",
                "followers_count": count,
                "follows_count": 180 + (day - start).days // 20,
                "media_count": sum(1 for p in posts if p.posted_at.date() <= day),
                "profile_picture_url": f"https://scontent.cdninstagram.com/{charity.handle}.jpg",
            }
        )
        info_times.append(_pull_time(day))

    media, insights = [], []
    for p in posts:
        m = _post_metrics(r, p, followers[p.posted_at.date()], now)
        record = {
            "id": p.post_id,
            "media_type": p.media_type,
            "media_product_type": p.product_type,
            "permalink": f"https://www.instagram.com/p/{p.post_id[-11:]}/",
            "timestamp": p.posted_at.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "like_count": m["likes"],
            "comments_count": m["comments"],
        }
        if p.caption:  # the API leaves the field out when there's no caption
            record["caption"] = p.caption
        media.append(record)
        insights.append(shape_media_insights(p.post_id, _insights_payload(r, p, m)))

    daily = []
    for i in range(min(730, (end - start).days)):
        day = end - timedelta(days=i + 1)
        recent = [
            p
            for p in posts
            if timedelta(0) <= day - p.posted_at.date() <= timedelta(days=3)
        ]
        reach = round(followers[day] * r.uniform(0.04, 0.09) * (1 + 1.5 * len(recent)))
        values = {
            "reach": reach,
            "views": round(reach * r.uniform(1.5, 2.5)),
            "accounts_engaged": round(reach * r.uniform(0.04, 0.08)),
            "likes": round(reach * r.uniform(0.03, 0.06)),
            "comments": round(reach * r.uniform(0.001, 0.004)),
            "shares": round(reach * r.uniform(0.002, 0.006)),
            "saves": round(reach * r.uniform(0.002, 0.006)),
            "reposts": round(reach * r.uniform(0, 0.001)),
            "total_interactions": 0,
            "profile_links_taps": round(reach * r.uniform(0.001, 0.005)),
        }
        values["total_interactions"] = sum(
            values[k] for k in ("likes", "comments", "shares", "saves")
        )
        daily.append(
            shape_account_day(
                day,
                {
                    "data": [
                        {"name": k, "total_value": {"value": v}}
                        for k, v in values.items()
                    ]
                },
            )
        )

    demographic_rows, demographic_times = [], []
    day = start
    while day <= end:
        drift = (day - start).days / max((end - start).days, 1)
        for breakdown, payload in _demographics_payloads(
            r, charity, followers[day], drift
        ).items():
            for row in shape_demographics(breakdown, payload):
                demographic_rows.append(row)
                demographic_times.append(_pull_time(day))
        day += timedelta(days=7)

    stories = []
    for i in range(min(730, (end - start).days)):
        day = end - timedelta(days=i + 1)
        if r.random() < charity.posts_per_week["instagram"] * 0.6 / 7:
            reach = round(followers[day] * r.uniform(0.05, 0.15))
            stories.append(
                {
                    "id": str(18_000_000_000_000_000 + r.randint(0, 999_999_999)),
                    "media_type": r.choice(("IMAGE", "VIDEO")),
                    "timestamp": datetime.combine(
                        day, time(r.randint(8, 21), r.randint(0, 59)), tzinfo=UTC
                    ).strftime("%Y-%m-%dT%H:%M:%S+0000"),
                    "reach": reach,
                    "views": round(reach * r.uniform(1.1, 1.5)),
                    "shares": round(reach * r.uniform(0, 0.01)),
                    "replies": round(reach * r.uniform(0, 0.005)),
                    "link_clicks": round(reach * r.uniform(0, 0.02)),
                    "navigation": round(reach * r.uniform(0.8, 1.2)),
                    "profile_visits": round(reach * r.uniform(0.005, 0.02)),
                    "follows": round(reach * r.uniform(0, 0.002)),
                }
            )

    return [
        Batch(
            "raw_instagram_account_info",
            info_rows,
            row_ingested_at=info_times,
            tags=tags,
        ),
        Batch("raw_instagram_media", media, ingested_at=now, tags=tags),
        Batch("raw_instagram_media_insights", insights, ingested_at=now, tags=tags),
        Batch(
            "raw_instagram_account_insights_daily", daily, ingested_at=now, tags=tags
        ),
        Batch(
            "raw_instagram_follower_demographics",
            demographic_rows,
            row_ingested_at=demographic_times,
            tags=tags,
        ),
        Batch("raw_instagram_stories", stories, ingested_at=now, tags=tags),
    ]


def tiktok_batches(
    charity: Charity, posts: list[Post], start: date, end: date, seed: int
) -> list[Batch]:
    r = rng(seed, charity.org_id, "tiktok-format")
    open_id = f"-000{r.getrandbits(64):x}"
    now = _pull_time(end)
    first = min((p.posted_at.date() for p in posts), default=end)
    followers = follower_series(r, first, end, charity.followers["tiktok"], posts)

    videos, insights, likes_by_day = [], [], {}
    for p in posts:
        views = max(
            50,
            round(
                followers[p.posted_at.date()]
                * r.lognormvariate(math.log(0.8), 1.2)
                * (1 + 3 * p.effect)
            ),
        )
        likes = round(views * r.uniform(0.03, 0.09))
        likes_by_day[p.posted_at.date()] = (
            likes_by_day.get(p.posted_at.date(), 0) + likes
        )
        duration = r.randint(9, 75)
        videos.append(
            {
                "id": p.post_id,
                "title": p.caption[:60],
                "video_description": p.caption,
                "create_time": int(p.posted_at.timestamp()),
                "duration": duration,
                "cover_image_url": f"https://p16-sign.tiktokcdn.com/{p.post_id}.jpeg",
                "share_url": f"https://www.tiktok.com/@{charity.handle}/video/{p.post_id}",
                "view_count": views,
                "like_count": likes,
                "comment_count": round(likes * r.uniform(0.01, 0.05)),
                "share_count": round(likes * r.uniform(0.03, 0.1)),
                # Display API fields not requested yet (see the capability reference)
                "embed_link": f"https://www.tiktok.com/embed/v2/{p.post_id}",
                "embed_html": f'<blockquote class="tiktok-embed" data-video-id="{p.post_id}"></blockquote>',
                "height": 1920,
                "width": 1080,
                "is_aigc": False,
            }
        )
        watched = round(duration * r.uniform(0.35, 0.8), 1)
        insights.append(
            {
                "video_id": p.post_id,
                "reach": round(views * r.uniform(0.7, 0.95)),
                "video_views": views,
                "total_time_watched": round(watched * views),
                "average_time_watched": watched,
                "full_video_watched_rate": round(r.uniform(0.08, 0.45), 3),
                "impression_sources": [
                    {"impression_source": s, "percentage": w}
                    for s, w in zip(
                        ("For You", "Follow", "Profile", "Search", "Sound"),
                        _split(r, 5),
                        strict=True,
                    )
                ],
                "audience_countries": [
                    {"country": c, "percentage": w}
                    for c, w in zip(
                        ("GB", "US", "PK", "IN"), _split(r, 4, first=0.7), strict=True
                    )
                ],
            }
        )

    user_rows, user_times, account_daily = [], [], []
    total_likes, previous = 0, None
    for day, count in followers.items():
        total_likes += likes_by_day.get(day, 0)
        user_rows.append(
            {
                "open_id": open_id,
                "display_name": charity.name,
                "follower_count": count,
                "following_count": 25,
                "likes_count": total_likes,
                "video_count": sum(1 for p in posts if p.posted_at.date() <= day),
                # Profile-scope fields (user.info.profile, not requested yet)
                "union_id": f"union-{open_id}",
                "avatar_url": f"https://p16-sign.tiktokcdn.com/avatar/{charity.handle}.jpeg",
                "avatar_url_100": f"https://p16-sign.tiktokcdn.com/avatar/{charity.handle}_100.jpeg",
                "avatar_large_url": f"https://p16-sign.tiktokcdn.com/avatar/{charity.handle}_large.jpeg",
                "username": charity.handle,
                "bio_description": f"{charity.name} 💚 UK charity",
                "profile_deep_link": f"https://www.tiktok.com/@{charity.handle}",
                "is_verified": False,
            }
        )
        user_times.append(_pull_time(day))
        gained = max(0, count - previous) if previous else 0
        account_daily.append(
            {
                "date": day.isoformat(),
                "followers_count": count,
                "followers_gained": gained + r.randint(0, 5),
                "followers_lost": r.randint(0, 5),
                "profile_views": round(count * r.uniform(0.002, 0.01)),
                "video_views": round(count * r.uniform(0.05, 0.6)),
            }
        )
        previous = count

    return [
        Batch("raw_tiktok_user_info", user_rows, row_ingested_at=user_times),
        Batch("raw_tiktok_videos", videos, ingested_at=now),
        Batch("raw_tiktok_video_insights", insights, ingested_at=now),
        Batch("raw_tiktok_account_insights_daily", account_daily, ingested_at=now),
    ]


def _split(r: random.Random, n: int, first: float | None = None) -> list[float]:
    weights = [r.random() for _ in range(n)]
    if first is not None:
        rest = sum(weights[1:]) or 1
        return [first] + [round((1 - first) * w / rest, 3) for w in weights[1:]]
    total = sum(weights)
    shares = sorted((round(w / total, 3) for w in weights), reverse=True)
    return shares
