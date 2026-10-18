"""Each charity's emails and social posts, with the effect (if any) each one has
on donations. Most have none: effects are drawn, never assumed."""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from synthetic import calendar
from synthetic.charities import Charity
from synthetic.rand import rng, uk_time_to_utc, weighted

# (probability, low, high) of an extra share of donations on the day of the
# event; half of it carries into the next day
EFFECTS = {
    "newsletter": ((0.78, 0, 0), (0.18, 0.05, 0.20), (0.04, 0.30, 0.80)),
    "appeal": ((0.55, 0, 0), (0.32, 0.10, 0.35), (0.13, 0.40, 1.20)),
    "post": ((0.88, 0, 0), (0.10, 0.03, 0.12), (0.02, 0.25, 0.70)),
}


def draw_effect(r: random.Random, kind: str) -> float:
    roll, cumulative = r.random(), 0.0
    for probability, low, high in EFFECTS[kind]:
        cumulative += probability
        if roll < cumulative:
            return round(r.uniform(low, high), 3) if high else 0.0
    return 0.0


@dataclass(frozen=True)
class Email:
    campaign_id: str
    title: str
    subject: str
    preview: str
    send_time: datetime
    kind: str  # newsletter or appeal
    effect: float


@dataclass(frozen=True)
class Post:
    post_id: str
    platform: str
    posted_at: datetime
    media_type: str  # IMAGE, CAROUSEL_ALBUM, VIDEO
    product_type: str | None  # FEED or REELS (Instagram only)
    caption: str
    theme: str
    effect: float


def _send_time(r: random.Random, day: date) -> datetime:
    hour = weighted(r, {7: 2, 8: 3, 9: 2, 12: 2, 13: 1, 17: 2, 18: 3, 19: 2})
    return uk_time_to_utc(day, hour, r.choice((0, 15, 30, 45)))


def _appeal_days(
    charity: Charity, start: date, end: date
) -> list[tuple[date, str, str]]:
    """(day, title, subject) for appeal emails tied to the charity's calendar."""
    days = []
    muslim = charity.ramadan_lift > 1
    for ramadan_start, eid in calendar.RAMADAN:
        if muslim:
            length = (eid - ramadan_start).days
            days += [
                (
                    ramadan_start,
                    "Ramadan Mubarak",
                    "Ramadan Mubarak 🌙 Your first fast, our first appeal",
                ),
                (
                    ramadan_start + timedelta(days=length - 10),
                    "The last 10 nights",
                    "The last 10 nights begin tonight ✨",
                ),
                (
                    ramadan_start + timedelta(days=25),
                    "Laylat al-Qadr",
                    "Tonight could be Laylat al-Qadr",
                ),
                (
                    eid - timedelta(days=2),
                    "Zakat al-Fitr reminder",
                    "Don't forget your Zakat al-Fitr",
                ),
            ]
    if muslim:
        for eid in calendar.EID_AL_ADHA:
            days.append(
                (
                    eid - timedelta(days=9),
                    "The best ten days",
                    "The best 10 days of the year start now",
                )
            )
            days.append(
                (
                    eid - timedelta(days=5),
                    "Qurbani closes soon",
                    "Last chance to book your Qurbani",
                )
            )
    if charity.december_lift > 1.2:
        for year in range(start.year, end.year + 1):
            days.append(
                (
                    date(year, 12, 1),
                    "Christmas appeal",
                    "This Christmas, give someone a future",
                )
            )
            days.append(
                (
                    date(year, 12, 15),
                    "Christmas appeal: final push",
                    "Ten days to go 🎄",
                )
            )
    for giving_tuesday in calendar.GIVING_TUESDAY:
        if charity.december_lift > 1.2:
            days.append(
                (
                    giving_tuesday,
                    "Giving Tuesday",
                    "It's Giving Tuesday: double your impact today",
                )
            )
    for projects in charity.projects.values():
        for project in projects:
            for fundraiser in project.fundraisers:
                if fundraiser.event_day:
                    event = date.fromisoformat(fundraiser.event_day)
                    days.append(
                        (
                            event - timedelta(days=21),
                            f"{project.name}: three weeks to go",
                            "Three weeks to go 🏃",
                        )
                    )
                    days.append(
                        (
                            event - timedelta(days=5),
                            f"{project.name}: this weekend",
                            "Cheer them on this weekend",
                        )
                    )
    if charity.emergency_day:
        emergency = date.fromisoformat(charity.emergency_day)
        days += [
            (emergency, "Emergency appeal", "URGENT: earthquake emergency appeal"),
            (
                emergency + timedelta(days=3),
                "Emergency appeal update",
                "What your donations are doing right now",
            ),
            (
                emergency + timedelta(days=14),
                "Emergency appeal: two weeks on",
                "Two weeks on: the need is still urgent",
            ),
        ]
    if charity.org_id == "demo_small":
        for year in range(start.year, end.year + 1):
            days.append(
                (
                    date(year, 11, 20),
                    "Winter Warmth appeal",
                    "Keep a Sparkbrook family warm this winter",
                )
            )
    # One email per day at most; keep those inside the window
    unique = {}
    for day, title, subject in days:
        if start <= day <= end:
            unique.setdefault(day, (day, title, subject))
    return sorted(unique.values())


NEWSLETTER_SUBJECTS = (
    "Your monthly update from {name}",
    "What you made possible this month",
    "News from {name} 💛",
    "Thank you — here's where your money went",
    "{name}: this month in pictures",
)


def emails_for(charity: Charity, start: date, end: date, seed: int) -> list[Email]:
    r = rng(seed, charity.org_id, "emails")
    emails = []
    for day, title, subject in _appeal_days(charity, start, end):
        emails.append(
            Email(
                campaign_id="",
                title=title,
                subject=subject,
                preview=f"A message from {charity.name}",
                send_time=_send_time(r, day),
                kind="appeal",
                effect=draw_effect(r, "appeal"),
            )
        )
    taken = {e.send_time.date() for e in emails}
    month = start.replace(day=1)
    while month <= end:
        for _ in range(charity.newsletters_per_month):
            day = month + timedelta(days=r.randint(2, 26))
            if start <= day <= end and day not in taken:
                taken.add(day)
                subject = r.choice(NEWSLETTER_SUBJECTS).format(name=charity.name)
                emails.append(
                    Email(
                        campaign_id="",
                        title=f"{month:%B %Y} newsletter",
                        subject=subject,
                        preview="Stories, updates and thank yous",
                        send_time=_send_time(r, day),
                        kind="newsletter",
                        effect=draw_effect(r, "newsletter"),
                    )
                )
        month = (month + timedelta(days=32)).replace(day=1)
    emails.sort(key=lambda e: e.send_time)
    return [
        Email(**{**e.__dict__, "campaign_id": f"{r.getrandbits(40):010x}"})
        for e in emails
    ]


CAPTIONS = {
    "appeal": (
        "Every donation counts. Link in bio to give today 🙏",
        "We're {pct}% of the way there. Can you help us close the gap?",
        "Your support makes this possible. Donate via the link in our bio.",
    ),
    "story": (
        "Meet one of the families you've helped this year ❤️",
        "This is what your generosity looks like on the ground.",
        "A small gift, a huge difference. Thank you for standing with us.",
    ),
    "update": (
        "Behind the scenes with our volunteers this week 📦",
        "Thank you to everyone who came along on Saturday!",
        "Quick update on where your donations went this month.",
    ),
    "ramadan": (
        "Ramadan Mubarak from all of us 🌙",
        "Iftar packs ready to go out tonight. JazakAllah khair to everyone who gave.",
        "The last 10 nights are here. Don't miss Laylat al-Qadr ✨",
    ),
}
HASHTAGS = ("#charity", "#givingback", "#community", "#volunteer", "#donate", "#uk")


def _ig_format(r: random.Random, progress: float) -> tuple[str, str]:
    reels_share = 0.10 + 0.35 * progress  # Reels take over across the three years
    kind = weighted(
        r, {"reel": reels_share, "carousel": 0.30, "image": 0.60 - reels_share}
    )
    return {
        "reel": ("VIDEO", "REELS"),
        "carousel": ("CAROUSEL_ALBUM", "FEED"),
        "image": ("IMAGE", "FEED"),
    }[kind]


def posts_for(
    charity: Charity, platform: str, start: date, end: date, seed: int
) -> list[Post]:
    r = rng(seed, charity.org_id, "posts", platform)
    weekly = charity.posts_per_week[platform]
    if platform == "tiktok":
        start = max(
            start, end - timedelta(days=730)
        )  # TikTok account started ~2 years ago
    posts, day, span = [], start, (end - start).days or 1
    while day <= end:
        rate = weekly / 7
        if calendar.in_ramadan(day) and charity.ramadan_lift > 1:
            rate *= 1.8
        if r.random() < min(rate, 0.95):
            progress = (day - start).days / span
            theme = weighted(
                r,
                {
                    "appeal": 3,
                    "story": 3,
                    "update": 3,
                    "ramadan": 4
                    if calendar.in_ramadan(day) and charity.ramadan_lift > 1
                    else 0,
                },
            )
            caption = r.choice(CAPTIONS[theme]).format(pct=r.randint(40, 95))
            if r.random() < 0.6:
                caption += " " + " ".join(r.sample(HASHTAGS, 3))
            if r.random() < 0.04:
                caption = ""  # some posts have no caption
            media_type, product = (
                ("VIDEO", None) if platform == "tiktok" else _ig_format(r, progress)
            )
            hour = weighted(
                r, {8: 1, 10: 1, 12: 3, 13: 2, 15: 1, 17: 2, 18: 3, 19: 3, 20: 2, 21: 1}
            )
            posts.append(
                Post(
                    post_id=str(
                        r.randint(17_800_000_000_000_000, 18_200_000_000_000_000)
                    )
                    if platform == "instagram"
                    else str(
                        r.randint(7_200_000_000_000_000_000, 7_499_999_999_999_999_999)
                    ),
                    platform=platform,
                    posted_at=uk_time_to_utc(
                        day, hour, r.randint(0, 59), r.randint(0, 59)
                    ),
                    media_type=media_type,
                    product_type=product,
                    caption=caption,
                    theme=theme,
                    effect=draw_effect(r, "post"),
                )
            )
        day += timedelta(days=1)
    return posts


def daily_lift(emails: list[Email], posts: list[Post]) -> dict[date, float]:
    """Extra share of donations per day caused by emails and posts."""
    lift: dict[date, float] = {}
    for event_day, effect in [(e.send_time.date(), e.effect) for e in emails] + [
        (p.posted_at.date(), p.effect) for p in posts
    ]:
        if effect:
            lift[event_day] = lift.get(event_day, 0) + effect
            lift[event_day + timedelta(days=1)] = (
                lift.get(event_day + timedelta(days=1), 0) + effect / 2
            )
    return lift
