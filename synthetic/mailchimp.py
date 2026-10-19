"""Mailchimp responses: campaign reports (with 24-hour timelines), audience
stats history, link clicks, daily activity and monthly growth — shaped by the
connector's own functions."""

import math
import random
from datetime import UTC, date, datetime, time, timedelta

from ingestion.mailchimp_campaigns import (
    shape_activity,
    shape_audience,
    shape_growth,
    shape_link_clicks,
    shape_report,
)
from synthetic.batches import Batch
from synthetic.charities import Charity
from synthetic.marketing import Email
from synthetic.rand import audience_series, rng

API = "https://us14.api.mailchimp.com/3.0"


def _ts(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _links(path: str, rels: tuple[str, ...]) -> list[dict]:
    return [
        {
            "rel": rel,
            "href": f"{API}/{path}" + ("" if rel in ("self", "parent") else f"/{rel}"),
            "method": "GET",
            "targetSchema": f"{API.replace('/3.0', '')}/schema/3.0/Definitions/{rel}.json",
            "schema": f"{API.replace('/3.0', '')}/schema/3.0/Paths/{rel}.json",
        }
        for rel in rels
    ]


REPORT_LINKS = (
    "parent",
    "self",
    "campaign",
    "sub-reports",
    "abuse-reports",
    "advice",
    "open-details",
    "click-details",
    "domain-performance",
    "eepurl",
    "email-activity",
    "locations",
    "sent-to",
    "unsubscribed",
)
LIST_LINKS = (
    "self",
    "parent",
    "update",
    "batch-sub-unsub-members",
    "delete",
    "abuse-reports",
    "activity",
    "clients",
    "growth-history",
    "interest-categories",
    "members",
    "merge-fields",
    "segments",
    "webhooks",
    "signup-forms",
    "locations",
)


def subscriber_series(
    r: random.Random,
    start: date,
    end: date,
    counts: tuple[int, int],
    emails: list[Email] = (),
) -> dict[date, int]:
    """Sign-ups pick up around appeals; each send loses a few unsubscribers
    that day and the next; Mailchimp cleans dead addresses about monthly."""
    bumps: dict[date, float] = {}
    drops: dict[date, float] = {}
    for e in emails:
        day = e.send_time.date()
        if e.kind == "appeal":
            bumps[day] = bumps.get(day, 0.0) + r.uniform(0.5, 2.5)
        lost = r.uniform(0.001, 0.004)
        drops[day] = drops.get(day, 0.0) + lost * 0.7
        drops[day + timedelta(days=1)] = (
            drops.get(day + timedelta(days=1), 0.0) + lost * 0.3
        )
    day = start
    while day <= end:
        if day.day == 1:
            clean = day + timedelta(days=r.randint(0, 6))
            drops[clean] = drops.get(clean, 0.0) + r.uniform(0.001, 0.005)
        day += timedelta(days=1)
    return audience_series(r, start, end, counts, bumps, drops)


def _report(
    r: random.Random,
    c: Charity,
    e: Email,
    list_id: str,
    sent_to: int,
    averages: tuple[float, float],
) -> dict:
    appeal = e.kind == "appeal"
    open_rate = min(0.75, max(0.15, r.gauss(0.40 if appeal else 0.36, 0.05)))
    proxy_open_rate = open_rate * r.uniform(0.55, 0.75)  # Apple Mail auto-opens removed
    click_rate = min(0.2, max(0.005, r.gauss(0.045 if appeal else 0.025, 0.012)))
    unique_opens = round(sent_to * open_rate)
    unique_clicks = round(sent_to * click_rate)
    # Opens arrive fast and tail off over the following hours
    weights = [math.exp(-h / 2.5) for h in range(24)]
    total_w = sum(weights)
    start_hour = e.send_time.replace(minute=0, second=0, microsecond=0)
    timeseries = []
    for h, w in enumerate(weights):
        opens_h = round(unique_opens * w / total_w)
        timeseries.append(
            {
                "timestamp": _ts(start_hour + timedelta(hours=h)),
                "emails_sent": sent_to if h == 0 else 0,
                "unique_opens": opens_h,
                "proxy_excluded_unique_opens": round(
                    opens_h * proxy_open_rate / open_rate
                ),
                "recipients_clicks": round(unique_clicks * w / total_w),
            }
        )
    return shape_report(
        {
            "id": e.campaign_id,
            "campaign_title": e.title,
            "type": "regular",
            "list_id": list_id,
            "list_is_active": True,
            "list_name": c.name,
            "subject_line": e.subject,
            "preview_text": e.preview,
            "emails_sent": sent_to,
            "abuse_reports": 1 if r.random() < 0.03 else 0,
            "unsubscribed": round(sent_to * r.uniform(0.0008, 0.004)),
            "send_time": _ts(e.send_time),
            "bounces": {
                "hard_bounces": round(sent_to * r.uniform(0, 0.003)),
                "soft_bounces": round(sent_to * r.uniform(0.001, 0.008)),
                "syntax_errors": 0,
            },
            "forwards": {
                "forwards_count": r.randint(0, 5),
                "forwards_opens": r.randint(0, 8),
            },
            "opens": {
                "opens_total": round(unique_opens * r.uniform(1.3, 1.8)),
                "proxy_excluded_opens": round(
                    unique_opens * proxy_open_rate / open_rate * 1.4
                ),
                "unique_opens": unique_opens,
                "proxy_excluded_unique_opens": round(
                    unique_opens * proxy_open_rate / open_rate
                ),
                "open_rate": round(open_rate, 4),
                "proxy_excluded_open_rate": round(proxy_open_rate, 4),
                "last_open": _ts(e.send_time + timedelta(days=r.randint(3, 20))),
            },
            "clicks": {
                "clicks_total": round(unique_clicks * r.uniform(1.2, 1.6)),
                "unique_clicks": unique_clicks,
                "unique_subscriber_clicks": unique_clicks,
                "click_rate": round(click_rate, 4),
                "last_click": _ts(e.send_time + timedelta(days=r.randint(1, 10))),
            },
            "facebook_likes": {
                "recipient_likes": 0,
                "unique_likes": 0,
                "facebook_likes": 0,
            },
            "list_stats": {
                "sub_rate": round(r.uniform(1, 4), 1),
                "unsub_rate": round(r.uniform(0.1, 0.8), 1),
                "open_rate": round(averages[0] * 100, 2),
                "proxy_excluded_open_rate": round(averages[0] * 70, 2),
                "click_rate": round(averages[1] * 100, 2),
            },
            "timeseries": timeseries,
            "ecommerce": {
                "total_orders": 0,
                "total_spent": 0.0,
                "total_revenue": 0.0,
                "currency_code": "USD",
            },
            "delivery_status": {"enabled": False},
            "_links": _links(f"reports/{e.campaign_id}", REPORT_LINKS),
        }
    )


def _audience(
    r: random.Random,
    c: Charity,
    list_id: str,
    web_id: int,
    created: date,
    members: int,
    sent: list[Email],
    day: date,
    unsubscribed: int,
) -> dict:
    return shape_audience(
        {
            "id": list_id,
            "web_id": web_id,
            "name": c.name,
            "contact": {
                "company": c.name,
                "address1": "1 High Street",
                "address2": "",
                "city": c.city,
                "state": "",
                "zip": "AB1 2CD",
                "country": "GB",
                "phone": "",
            },
            "permission_reminder": f"You signed up to hear from {c.name}.",
            "use_archive_bar": True,
            "campaign_defaults": {
                "from_name": c.name,
                "from_email": f"hello@{c.handle.replace('.', '')}.example.com",
                "subject": "",
                "language": "en",
            },
            "notify_on_subscribe": "",
            "notify_on_unsubscribe": "",
            "date_created": _ts(datetime.combine(created, time(10), tzinfo=UTC)),
            "list_rating": 3,
            "email_type_option": False,
            "subscribe_url_short": f"http://eepurl.com/{list_id[:6]}",
            "subscribe_url_long": f"https://{c.handle.replace('.', '')}.us14.list-manage.com/subscribe?id={list_id}",
            "beamer_address": f"us14-{list_id}@inbound.mailchimp.com",
            "visibility": "prv",
            "double_optin": False,
            "has_welcome": False,
            "marketing_permissions": False,
            "modules": [],
            "stats": {
                "member_count": members,
                "unsubscribe_count": unsubscribed,
                "cleaned_count": round(members * 0.02),
                "member_count_since_send": r.randint(0, 25),
                "unsubscribe_count_since_send": r.randint(0, 5),
                "cleaned_count_since_send": r.randint(0, 3),
                "campaign_count": len(sent),
                "campaign_last_sent": _ts(sent[-1].send_time) if sent else "",
                "merge_field_count": 3,
                "avg_sub_rate": round(r.uniform(1, 4), 1),
                "avg_unsub_rate": round(r.uniform(0.1, 0.8), 1),
                "target_sub_rate": round(r.uniform(1, 3), 1),
                "open_rate": round(r.uniform(32, 42), 2),
                "click_rate": round(r.uniform(2, 4.5), 2),
                "last_sub_date": _ts(datetime.combine(day, time(9), tzinfo=UTC)),
                "last_unsub_date": _ts(
                    datetime.combine(
                        day - timedelta(days=r.randint(0, 6)), time(15), tzinfo=UTC
                    )
                ),
            },
            "_links": _links(f"lists/{list_id}", LIST_LINKS),
        }
    )


def batches(
    c: Charity, emails: list[Email], start: date, end: date, seed: int
) -> list[Batch]:
    r = rng(seed, c.org_id, "mailchimp-format")
    list_id, web_id = f"{r.getrandbits(40):010x}", r.randint(100_000, 999_999)
    subscribers = subscriber_series(r, start, end, c.subscribers, emails)
    now = datetime.combine(end, time(6), tzinfo=UTC)
    averages = (0.37, 0.03)

    reports, clicks = [], []
    for e in emails:
        sent_to = round(subscribers[e.send_time.date()] * 0.97)
        report = _report(r, c, e, list_id, sent_to, averages)
        reports.append(report)
        total = report["clicks"]["clicks_total"]
        options = list(c.links)
        weights = [
            3 if "onat" in name or "Give" in name or "Zakat" in name else 1
            for name in options
        ]
        chosen = r.sample(range(len(options)), k=min(len(options), r.randint(2, 4)))
        share = [weights[i] * r.uniform(0.5, 1.5) for i in chosen]
        for i, w in zip(chosen, share, strict=True):
            link_clicks = round(total * w / sum(share))
            clicks.append(
                {
                    "id": f"{r.getrandbits(40):010x}",
                    "url": f"https://{c.handle.replace('.', '')}.example.org/{options[i].lower().replace(' ', '-')}",
                    "total_clicks": link_clicks,
                    "click_percentage": round(link_clicks / total, 4) if total else 0,
                    "unique_clicks": round(link_clicks * 0.8),
                    "unique_click_percentage": round(link_clicks / total, 4)
                    if total
                    else 0,
                    "last_click": report["clicks"]["last_click"],
                    "campaign_id": e.campaign_id,
                    "_links": _links(
                        f"reports/{e.campaign_id}/click-details", ("parent", "self")
                    ),
                }
            )

    audiences, audience_times, unsubscribed = [], [], 0
    for day, members in subscribers.items():
        unsubscribed += r.randint(0, 3)
        sent = [e for e in emails if e.send_time.date() <= day]
        audiences.append(
            _audience(r, c, list_id, web_id, start, members, sent, day, unsubscribed)
        )
        audience_times.append(datetime.combine(day, time(6), tzinfo=UTC))

    # Mailchimp's daily activity covers a rolling ~180 days; one pull a month
    sends_by_day = {e.send_time.date(): e for e in emails}
    report_by_id = {rep["id"]: rep for rep in reports}
    # Daily sign-ups and unsubscribes, computed once so the daily activity and
    # the monthly growth history agree with each other
    daily_subs, daily_unsubs = {}, {}
    for day in subscribers:
        e = sends_by_day.get(day)
        rep = report_by_id[e.campaign_id] if e else None
        unsubs = r.randint(0, 3) + (rep["unsubscribed"] if rep else 0)
        net = subscribers[day] - subscribers.get(
            day - timedelta(days=1), subscribers[day]
        )
        daily_unsubs[day] = unsubs
        daily_subs[day] = max(0, net + unsubs) + r.randint(0, 2)

    activity, activity_times = [], []
    pull = start + timedelta(days=30)
    while pull <= end:
        window = [
            pull - timedelta(days=i)
            for i in range(180)
            if pull - timedelta(days=i) >= start
        ]
        rows = []
        for day in window:
            e = sends_by_day.get(day)
            rep = report_by_id[e.campaign_id] if e else None
            rows.append(
                {
                    "day": day.isoformat(),
                    "emails_sent": rep["emails_sent"] if rep else 0,
                    "unique_opens": rep["opens"]["unique_opens"] if rep else 0,
                    "recipient_clicks": rep["clicks"]["unique_clicks"] if rep else 0,
                    "hard_bounce": rep["bounces"]["hard_bounces"] if rep else 0,
                    "soft_bounce": rep["bounces"]["soft_bounces"] if rep else 0,
                    # Form sign-ups only; imports and manual adds show as other_adds
                    "subs": daily_subs[day],
                    "unsubs": daily_unsubs[day],
                    "other_adds": r.randint(0, 1),
                    "other_removes": r.randint(0, 1),
                }
            )
        for row in shape_activity(list_id, rows):
            activity.append(row)
            activity_times.append(datetime.combine(pull, time(6), tzinfo=UTC))
        pull += timedelta(days=30)

    growth, month = [], start.replace(day=1)
    while month <= end:
        next_month = (month + timedelta(days=32)).replace(day=1)
        inside = [d for d in subscribers if month <= d < next_month]
        growth.append(
            {
                "list_id": list_id,
                "month": month.strftime("%Y-%m"),
                "existing": subscribers[min(inside)],
                "imports": 0,
                "optins": 0,
                "subscribed": sum(daily_subs[d] for d in inside),
                "unsubscribed": sum(daily_unsubs[d] for d in inside),
                "reconfirm": 0,
                "cleaned": round(subscribers[min(inside)] * r.uniform(0.001, 0.005)),
                "pending": r.randint(0, 4),
                "deleted": 0,
                "transactional": 0,
                "_links": _links(
                    f"lists/{list_id}/growth-history/{month:%Y-%m}", ("self", "parent")
                ),
            }
        )
        month = next_month

    return [
        Batch("raw_mailchimp_campaign_reports", reports, ingested_at=now),
        Batch(
            "raw_mailchimp_audience_stats", audiences, row_ingested_at=audience_times
        ),
        Batch(
            "raw_mailchimp_campaign_link_clicks",
            shape_link_clicks(clicks),
            ingested_at=now,
        ),
        Batch(
            "raw_mailchimp_list_activity_daily",
            activity,
            row_ingested_at=activity_times,
        ),
        Batch(
            "raw_mailchimp_list_growth_monthly", shape_growth(growth), ingested_at=now
        ),
    ]
