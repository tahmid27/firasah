"""The three demo charities. Internal org IDs are stable; display names are for the UI."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fundraiser:
    name: str
    target: float = 0.0  # 0 = no target
    weight: float = 1.0  # share of the project's donations
    owner: str | None = None
    event_day: str | None = None  # ISO date of a sponsored event, if any
    # when it collects: always, ramadan, dhul_hijjah, december, winter, event, emergency
    season: str = "always"


@dataclass(frozen=True)
class Project:
    name: str
    fundraisers: tuple[Fundraiser, ...]
    weight: float = 1.0
    zakat_eligible: bool = False


@dataclass(frozen=True)
class Charity:
    org_id: str
    name: str
    city: str
    yearly_donations: int
    # share of donations per platform, e.g. {"justgiving": 0.6, "launchgood": 0.4}
    donation_platforms: dict[str, float]
    projects: dict[str, tuple[Project, ...]]  # per platform
    social: tuple[str, ...]
    followers: dict[str, tuple[int, int]]  # platform -> (3 years ago, today)
    subscribers: tuple[int, int]
    posts_per_week: dict[str, float]
    newsletters_per_month: int
    ramadan_lift: float
    last_ten_nights_lift: float
    dhul_hijjah_lift: float
    december_lift: float
    gift_aid_rate: float
    muslim_donor_share: float
    non_gbp_donations: int
    cities: tuple[str, ...]
    handle: str
    links: tuple[str, ...] = field(default=())
    emergency_day: str | None = None  # start of a one-off emergency appeal


AL_NOOR = Charity(
    org_id="demo_small",
    name="Al-Noor Community Trust",
    city="Birmingham",
    yearly_donations=1_500,
    donation_platforms={"launchgood": 1.0},
    projects={
        "launchgood": (
            Project(
                "Al-Noor Ramadan Food Packs",
                (
                    Fundraiser("Ramadan Food Packs", weight=3, season="ramadan"),
                    Fundraiser(
                        "Sisters' Iftar Challenge", weight=1.5, season="ramadan"
                    ),
                    Fundraiser("Yusuf's 30 Days of Giving", weight=1, season="ramadan"),
                ),
                weight=3,
                zakat_eligible=True,
            ),
            Project(
                "Al-Noor Masjid Extension Fund",
                (
                    Fundraiser("Masjid Extension: Brick by Brick", weight=3),
                    Fundraiser("Brothers' Charity Walk for the Masjid", weight=1),
                ),
                weight=2,
            ),
            Project(
                "Al-Noor Orphan Sponsorship",
                (Fundraiser("Sponsor an Orphan with Al-Noor", weight=1),),
                weight=1.5,
                zakat_eligible=True,
            ),
            Project(
                "Al-Noor Winter Warmth Appeal",
                (
                    Fundraiser(
                        "Winter Warmth for Sparkbrook Families",
                        weight=1,
                        season="winter",
                    ),
                ),
                weight=1,
            ),
        )
    },
    social=("instagram",),
    followers={"instagram": (420, 1_850)},
    subscribers=(300, 1_200),
    posts_per_week={"instagram": 2.0},
    newsletters_per_month=1,
    ramadan_lift=4.0,
    last_ten_nights_lift=8.0,
    dhul_hijjah_lift=2.5,
    december_lift=1.1,
    gift_aid_rate=0.5,
    muslim_donor_share=0.95,
    non_gbp_donations=0,
    cities=("Birmingham", "Walsall", "Wolverhampton", "Coventry", "London", "Bradford"),
    handle="alnoor.trust",
    links=("Donate now", "Read our Ramadan update", "Volunteer with us"),
)

BRIGHTWATER = Charity(
    org_id="demo_medium",
    name="Brightwater Foundation",
    city="Bristol",
    yearly_donations=8_000,
    donation_platforms={"justgiving": 1.0},
    projects={
        "justgiving": (
            Project(
                "Brightwater Riverside Half Marathon",
                (
                    Fundraiser(
                        "Sarah's Riverside Half for Brightwater",
                        750,
                        2,
                        "Sarah Mitchell",
                        "2025-09-14",
                        season="event",
                    ),
                    Fundraiser(
                        "Team Riverside Runners",
                        3_000,
                        3,
                        "Tom Fletcher",
                        "2025-09-14",
                        season="event",
                    ),
                    Fundraiser(
                        "Dan runs his first half marathon",
                        500,
                        1,
                        "Dan Hughes",
                        "2025-09-14",
                        season="event",
                    ),
                    Fundraiser(
                        "Priya's Riverside Half 2024",
                        600,
                        1,
                        "Priya Shah",
                        "2024-09-15",
                        season="event",
                    ),
                ),
                weight=3,
            ),
            Project(
                "Brightwater Clean Water Appeal",
                (
                    Fundraiser(
                        "Brightwater Clean Water Appeal",
                        25_000,
                        4,
                        "Brightwater Foundation",
                    ),
                    Fundraiser(
                        "Year 6 bake sale for clean water", 300, 0.5, "Lucy Evans"
                    ),
                ),
                weight=3,
            ),
            Project(
                "Brightwater Big Swim",
                (
                    Fundraiser(
                        "James swims 5k for clean water",
                        1_000,
                        1.5,
                        "James Carter",
                        "2026-06-20",
                        season="event",
                    ),
                    Fundraiser(
                        "The Harbourside Swimmers",
                        2_500,
                        2,
                        "Emma Clarke",
                        "2026-06-20",
                        season="event",
                    ),
                ),
                weight=2,
            ),
            Project(
                "Brightwater Christmas Appeal",
                (
                    Fundraiser(
                        "Brightwater Christmas Appeal",
                        10_000,
                        1,
                        "Brightwater Foundation",
                        season="december",
                    ),
                ),
                weight=2,
            ),
        )
    },
    social=("instagram",),
    followers={"instagram": (2_100, 5_900)},
    subscribers=(2_000, 5_500),
    posts_per_week={"instagram": 3.0},
    newsletters_per_month=2,
    ramadan_lift=1.0,
    last_ten_nights_lift=1.0,
    dhul_hijjah_lift=1.0,
    december_lift=1.7,
    gift_aid_rate=0.65,
    muslim_donor_share=0.05,
    non_gbp_donations=3,
    cities=("Bristol", "Bath", "Cardiff", "Swindon", "London", "Exeter"),
    handle="brightwaterfoundation",
    links=(
        "Donate now",
        "Sign up for the Big Swim",
        "See where your money goes",
        "Read the full story",
    ),
)

UNITY = Charity(
    org_id="demo_large",
    name="Unity Relief",
    city="London",
    yearly_donations=25_000,
    donation_platforms={"justgiving": 0.6, "launchgood": 0.4},
    projects={
        "justgiving": (
            Project(
                "Unity Relief Where Most Needed",
                (
                    Fundraiser("Unity Relief: Where Most Needed", 0, 3, "Unity Relief"),
                    Fundraiser("Monthly givers: Unity Relief", 0, 1, "Unity Relief"),
                ),
                weight=2,
            ),
            Project(
                "Unity Relief Earthquake Emergency Response",
                (
                    Fundraiser(
                        "Unity Relief Earthquake Emergency Appeal",
                        150_000,
                        5,
                        "Unity Relief",
                        season="emergency",
                    ),
                    Fundraiser(
                        "Bradford Grand Mosque earthquake drive",
                        20_000,
                        1.5,
                        "Imran Malik",
                        season="emergency",
                    ),
                    Fundraiser(
                        "Aisha's sponsored silence",
                        500,
                        0.3,
                        "Aisha Rahman",
                        season="emergency",
                    ),
                ),
                weight=3,
            ),
            Project(
                "Unity Relief Winter Survival Appeal",
                (
                    Fundraiser(
                        "Unity Relief Winter Survival Appeal",
                        80_000,
                        3,
                        "Unity Relief",
                        season="winter",
                    ),
                    Fundraiser(
                        "Big Sleep Out for Winter Survival",
                        5_000,
                        1,
                        "Hassan Ali",
                        season="winter",
                    ),
                ),
                weight=2,
            ),
            Project(
                "Unity Relief London 10K",
                (
                    Fundraiser(
                        "Team Unity London 10K 2025",
                        15_000,
                        2,
                        "Unity Relief",
                        "2025-07-13",
                        season="event",
                    ),
                    Fundraiser(
                        "Bilal runs the London 10K",
                        1_000,
                        0.7,
                        "Bilal Ahmed",
                        "2025-07-13",
                        season="event",
                    ),
                    Fundraiser(
                        "Sana's first 10K",
                        750,
                        0.5,
                        "Sana Iqbal",
                        "2025-07-13",
                        season="event",
                    ),
                ),
                weight=1.5,
            ),
        ),
        "launchgood": (
            Project(
                "Unity Relief Ramadan Iftar Appeal",
                (
                    Fundraiser("Feed a Fasting Family", weight=3, season="ramadan"),
                    Fundraiser(
                        "Last 10 Nights with Unity Relief", weight=2, season="ramadan"
                    ),
                ),
                weight=3,
                zakat_eligible=True,
            ),
            Project(
                "Unity Relief Zakat Fund",
                (Fundraiser("Pay Your Zakat with Unity Relief", weight=1),),
                weight=2.5,
                zakat_eligible=True,
            ),
            Project(
                "Unity Relief Water Wells",
                (
                    Fundraiser("Build a Water Well", weight=2),
                    Fundraiser("Sadaqah Jariyah: Wells for Villages", weight=1),
                ),
                weight=1.5,
            ),
            Project(
                "Unity Relief Qurbani",
                (
                    Fundraiser(
                        "Qurbani with Unity Relief", weight=1, season="dhul_hijjah"
                    ),
                ),
                weight=1.5,
            ),
        ),
    },
    social=("instagram", "tiktok"),
    followers={"instagram": (15_000, 42_000), "tiktok": (2_500, 26_000)},
    subscribers=(12_000, 30_000),
    posts_per_week={"instagram": 5.0, "tiktok": 3.0},
    newsletters_per_month=3,
    ramadan_lift=2.5,
    last_ten_nights_lift=4.0,
    dhul_hijjah_lift=2.0,
    december_lift=1.8,
    gift_aid_rate=0.55,
    muslim_donor_share=0.7,
    non_gbp_donations=4,
    cities=(
        "London",
        "Birmingham",
        "Manchester",
        "Bradford",
        "Leicester",
        "Leeds",
        "Luton",
        "Glasgow",
    ),
    handle="unityrelief",
    emergency_day="2025-11-04",
    links=(
        "Give now",
        "Pay your Zakat",
        "Watch the appeal video",
        "Read the field report",
    ),
)

CHARITIES = (AL_NOOR, BRIGHTWATER, UNITY)
