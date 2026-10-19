"""Donations per charity and platform: a day-by-day giving model (seasons,
paydays, growth, noise, and whatever effect emails and posts happen to have),
then amounts, times, donors, Gift Aid and Zakat per donation."""

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from faker import Faker

from synthetic import calendar
from synthetic.charities import Charity, Fundraiser, Project
from synthetic.rand import rng, uk_time_to_utc, weighted

MUSLIM_FIRST = (
    "Mohammed",
    "Muhammad",
    "Ahmed",
    "Ali",
    "Omar",
    "Yusuf",
    "Ibrahim",
    "Hassan",
    "Bilal",
    "Imran",
    "Zain",
    "Hamza",
    "Adam",
    "Idris",
    "Tariq",
    "Aisha",
    "Fatima",
    "Maryam",
    "Zainab",
    "Khadija",
    "Amina",
    "Hafsa",
    "Sana",
    "Noor",
    "Safiya",
    "Hana",
    "Layla",
    "Sumayyah",
    "Ruqayyah",
    "Iman",
)
MUSLIM_LAST = (
    "Khan",
    "Ahmed",
    "Hussain",
    "Ali",
    "Rahman",
    "Begum",
    "Patel",
    "Iqbal",
    "Malik",
    "Shah",
    "Mahmood",
    "Akhtar",
    "Choudhury",
    "Uddin",
    "Miah",
    "Hassan",
    "Bhatti",
    "Qureshi",
    "Siddiqui",
    "Islam",
)
JG_MESSAGES = (
    "Good luck! You've got this 💪",
    "So proud of you, go smash it!",
    "In memory of Mum ❤️",
    "Keep up the brilliant work",
    "Happy to support such a great cause",
    "Well done, what an achievement!",
    "For everyone affected. Thinking of you all.",
    "Love from all of us x",
)
LG_COMMENTS = (
    "Ramadan Mubarak",
    "May Allah accept from all of us",
    "On behalf of my late father, please make dua for him",
    "JazakAllah khair for all your work",
    "For the sake of Allah",
    "Sadaqah for my family",
)
LG_TRAFFIC = {
    "internal_comm_page": 0.35,
    "campaign_page": 0.25,
    "whatsapp": 0.15,
    "facebook": 0.10,
    "instagram": 0.08,
    "email": 0.07,
}
FOREIGN = {"USD": 1.27, "EUR": 1.17}  # per GBP


@dataclass
class Donor:
    donor_id: int
    first: str
    last: str
    email: str
    city: str
    uk_taxpayer: bool
    ticks_gift_aid: bool
    anonymous: bool
    marketing_consent: bool


@dataclass
class Donation:
    donation_id: int
    platform: str
    project: Project
    fundraiser: Fundraiser
    at: datetime
    amount: float
    currency: str
    donor: Donor
    is_gift_aid: bool
    is_zakat: bool
    traffic_source: str
    message: str
    refunded: bool = False
    online: bool = True
    nightly: bool = False
    extra: dict = field(default_factory=dict)


def _in_season(f: Fundraiser, day: date, emergency: date | None) -> float:
    """How strongly a fundraiser collects on a given day (0 = not at all)."""
    if f.season == "always":
        return 1.0
    if f.season == "ramadan":
        if calendar.in_ramadan(day):
            return 3.0
        return 0.6 if calendar.in_ramadan(day + timedelta(days=7)) else 0.0
    if f.season == "dhul_hijjah":
        if calendar.in_dhul_hijjah_ten(day):
            return 4.0
        return 1.0 if calendar.in_dhul_hijjah_ten(day + timedelta(days=14)) else 0.0
    if f.season == "december":
        return (
            3.0
            if (day.month == 12 and day.day <= 31)
            or (day.month == 11 and day.day >= 15)
            else 0.0
        )
    if f.season == "winter":
        return 2.0 if day.month in (11, 12, 1, 2) else 0.0
    if f.season == "event":
        event = date.fromisoformat(f.event_day)
        to_go = (event - day).days
        if 0 <= to_go <= 70:
            return 1.0 + 3.0 * (1 - to_go / 70)  # builds towards the day
        return 1.5 if -14 <= to_go < 0 else 0.0
    if f.season == "emergency" and emergency:
        since = (day - emergency).days
        return 6.0 * math.exp(-since / 20) + 0.3 if 0 <= since <= 150 else 0.0
    return 0.0


def _day_multiplier(c: Charity, platform: str, day: date, progress: float) -> float:
    m = 1.0 + 0.35 * progress  # gradual growth over the three years
    m *= {0: 1.0, 1: 0.95, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.05, 6: 1.1}[day.weekday()]
    # Ramadan-heavy giving is a LaunchGood pattern; JustGiving donors less so
    strength = 1.0 if platform == "launchgood" else 0.3
    if calendar.in_ramadan(day):
        m *= 1 + (c.ramadan_lift - 1) * strength
        if calendar.in_last_ten_nights(day):
            m *= 1 + (c.last_ten_nights_lift / c.ramadan_lift - 1) * strength
        if calendar.is_27th_night(day):
            m *= 1 + 0.8 * strength
    if calendar.in_dhul_hijjah_ten(day):
        m *= 1 + (c.dhul_hijjah_lift - 1) * strength
    if day.month == 12:
        m *= c.december_lift
    if day in calendar.GIVING_TUESDAY and c.december_lift > 1.2:
        m *= 3.0
    if calendar.is_payday_window(day):
        m *= 1.15
    if c.emergency_day:
        since = (day - date.fromisoformat(c.emergency_day)).days
        if 0 <= since <= 150:
            m *= 1 + 5.0 * math.exp(-since / 15)
    return m


def _hour(r: random.Random, day: date) -> int:
    weights = {h: 1.0 for h in range(24)}
    for h in range(7):
        weights[h] = 0.15
    for h, w in {12: 2.0, 13: 2.0, 19: 2.5, 20: 3.0, 21: 3.0, 22: 2.0, 23: 1.0}.items():
        weights[h] = w
    if calendar.in_ramadan(day):
        for h, w in {3: 1.5, 4: 2.0, 5: 1.2, 21: 4.0, 22: 4.0, 23: 3.0, 0: 1.5}.items():
            weights[h] = w  # suhoor and after taraweeh
    return weighted(r, weights)


class DonorPool:
    def __init__(self, c: Charity, platform: str, seed: int):
        self.r = rng(seed, c.org_id, platform, "donors")
        self.fake = Faker("en_GB")
        self.fake.seed_instance(self.r.getrandbits(32))
        self.c, self.donors, self.next_id = c, [], 1

    def new(self) -> Donor:
        r, c = self.r, self.c
        if r.random() < c.muslim_donor_share:
            first, last = r.choice(MUSLIM_FIRST), r.choice(MUSLIM_LAST)
        else:
            first, last = self.fake.first_name(), self.fake.last_name()
        donor = Donor(
            donor_id=self.next_id,
            first=first,
            last=last,
            email=f"{first}.{last}.{self.next_id}@example.com".lower().replace("'", ""),
            city=r.choice(c.cities),
            uk_taxpayer=r.random() < 0.9,
            ticks_gift_aid=r.random() < c.gift_aid_rate / 0.9,
            anonymous=r.random() < 0.18,
            marketing_consent=r.random() < 0.4,
        )
        self.next_id += 1
        self.donors.append(donor)
        return donor

    def pick(self) -> Donor:
        if self.donors and self.r.random() < 0.3:
            # Popular donors give again more often (a long tail of repeat givers)
            index = int(len(self.donors) * (self.r.random() ** 2.5))
            return self.donors[index]
        return self.new()


def _amount(
    r: random.Random, c: Charity, f: Fundraiser, zakat: bool, nightly: bool
) -> float:
    if nightly:
        return float(r.choice((1, 2, 3, 5, 5, 10)))
    if zakat:
        return round(r.lognormvariate(math.log(220), 0.8))
    if r.random() < (0.003 if c.yearly_donations > 5_000 else 0.0005):
        return float(r.choice((500, 750, 1_000, 2_000, 5_000)))  # occasional major gift
    if f.season == "event":
        return float(weighted(r, {5: 2, 10: 5, 15: 2, 20: 4, 25: 2, 30: 1, 50: 1}))
    if r.random() < 0.7:
        return float(weighted(r, {5: 2, 10: 5, 20: 3, 25: 3, 30: 1, 50: 3, 100: 1.2}))
    value = r.lognormvariate(math.log(35), 0.9)
    return float(round(value)) if r.random() < 0.85 else round(value, 2)


def donations_for(
    c: Charity,
    platform: str,
    start: date,
    end: date,
    lift: dict[date, float],
    seed: int,
) -> list[Donation]:
    r = rng(seed, c.org_id, platform, "donations")
    pool = DonorPool(c, platform, seed)
    emergency = date.fromisoformat(c.emergency_day) if c.emergency_day else None
    span = (end - start).days or 1
    days = [start + timedelta(days=i) for i in range(span + 1)]
    multipliers = [
        _day_multiplier(c, platform, d, i / span) for i, d in enumerate(days)
    ]
    yearly = c.yearly_donations * c.donation_platforms[platform]
    base = yearly * (span + 1) / 365 / sum(multipliers)

    donations: list[Donation] = []
    next_id = (1_600_000_000 if platform == "justgiving" else 26_000_000) + r.randint(
        0, 99_999
    )
    nightly_donors: list[Donor] = []
    # A supporter's own page (a bake sale, a 10K) runs until it has raised
    # roughly its target, then stops collecting. Its own random stream, so
    # caps don't shift anything else that's generated.
    cap_r = rng(seed, c.org_id, platform, "page-caps")
    caps = {
        f: f.target * cap_r.lognormvariate(0.1, 0.3)
        for project in c.projects[platform]
        for f in project.fundraisers
        if f.target and f.owner not in (None, c.name)
    }
    raised: dict[Fundraiser, float] = {}
    for day, multiplier in zip(days, multipliers, strict=True):
        noise = r.gammavariate(6, 1 / 6)
        expected = base * multiplier * noise * (1 + lift.get(day, 0.0))
        count = _poisson(r, expected)
        active = [
            (project, f, project.weight * f.weight * _in_season(f, day, emergency))
            for project in c.projects[platform]
            for f in project.fundraisers
        ]

        def open_(f: Fundraiser) -> bool:
            return f not in caps or raised.get(f, 0.0) < caps[f]

        active = [a for a in active if a[2] > 0 and open_(a[1])]
        if not active:
            active = [
                (p, f, 1.0)
                for p in c.projects[platform]
                for f in p.fundraisers
                if open_(f)
            ]
        if not active:
            continue
        if (
            calendar.in_last_ten_nights(day)
            and platform == "launchgood"
            and not nightly_donors
        ):
            nightly_donors = [pool.new() for _ in range(max(3, int(yearly / 120)))]
        for _ in range(count):
            project, fundraiser, _w = r.choices(active, weights=[a[2] for a in active])[
                0
            ]
            nightly = (
                platform == "launchgood"
                and calendar.in_last_ten_nights(day)
                and r.random() < 0.3
            )
            donor = r.choice(nightly_donors) if nightly else pool.pick()
            zakat_chance = (
                (0.4 if calendar.in_ramadan(day) else 0.12)
                if project.zakat_eligible
                else 0
            )
            is_zakat = (
                platform == "launchgood" and not nightly and r.random() < zakat_chance
            )
            hour = 22 if nightly else _hour(r, day)
            amount = _amount(r, c, fundraiser, is_zakat, nightly)
            raised[fundraiser] = raised.get(fundraiser, 0.0) + amount
            donations.append(
                Donation(
                    donation_id=next_id,
                    platform=platform,
                    project=project,
                    fundraiser=fundraiser,
                    at=uk_time_to_utc(day, hour, r.randint(0, 59), r.randint(0, 59)),
                    amount=amount,
                    currency="GBP",
                    donor=donor,
                    is_gift_aid=donor.uk_taxpayer
                    and donor.ticks_gift_aid
                    and not is_zakat,
                    is_zakat=is_zakat,
                    traffic_source=(
                        weighted(r, LG_TRAFFIC)
                        if platform == "launchgood"
                        else "SponsoredDonationCampaign"
                        if fundraiser.owner != c.name
                        else "Direct"
                    ),
                    message=(
                        r.choice(
                            JG_MESSAGES if platform == "justgiving" else LG_COMMENTS
                        )
                        if r.random() < (0.3 if platform == "justgiving" else 0.15)
                        else ""
                    ),
                    refunded=r.random()
                    < (0.006 if platform == "justgiving" else 0.004),
                    online=platform == "justgiving" or r.random() > 0.03,
                    nightly=nightly,
                )
            )
            next_id += r.randint(1, 40)
        if not calendar.in_ramadan(day):
            nightly_donors = []

    # A few donations in another currency (medium and large charities only)
    share = round(c.non_gbp_donations * c.donation_platforms[platform])
    for donation in r.sample(donations, min(share, len(donations))):
        donation.currency = r.choice(list(FOREIGN))
        donation.amount = float(r.choice((20, 25, 50, 100)))
        donation.is_gift_aid = False
    return donations


def _poisson(r: random.Random, mean: float) -> int:
    if mean > 50:
        return max(0, round(r.gauss(mean, math.sqrt(mean))))
    threshold, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= r.random()
        if p <= threshold:
            return k
        k += 1
