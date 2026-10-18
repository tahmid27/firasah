"""JustGiving page-details and donations responses, shaped by the connector's
own functions."""

import re
import uuid
from datetime import datetime, timedelta

from ingestion.justgiving_donations import shape_donation, shape_page_details
from synthetic.batches import Batch
from synthetic.charities import Charity
from synthetic.donations import Donation
from synthetic.rand import rng


def _dotnet(at: datetime) -> str:
    return f"/Date({int(at.timestamp() * 1000)}+0000)/"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def _donation_record(d: Donation, charity_id: int, r) -> dict:
    donor = d.donor
    if donor.anonymous:
        display = "Anonymous"
    elif r.random() < 0.2:
        display = donor.first
    else:
        display = f"{donor.first} {donor.last}"
    record = {
        "amount": str(d.amount),
        "currencyCode": d.currency,
        "donationDate": _dotnet(d.at),
        "donationRef": None,
        "donorDisplayName": display,
        "donorLocalAmount": str(d.amount),
        "donorLocalCurrencyCode": d.currency,
        "id": d.donation_id,
        "message": d.message,
        "source": d.traffic_source,
        "thirdPartyReference": None,
        "charityId": charity_id,
    }
    if r.random() < 0.7:
        record["image"] = (
            "https://images.justgiving.com/image/avatars/default-avatar.gif"
        )
    return shape_donation(record)


def _page_body(
    charity: Charity,
    charity_id: int,
    event_ids: dict,
    fundraiser,
    project,
    donations,
    r,
) -> dict:
    gbp = [d for d in donations if d.currency == "GBP" and not d.refunded]
    raised = round(sum(d.amount for d in gbp), 2)
    gift_aid = round(sum(d.amount for d in gbp if d.is_gift_aid) * 0.25, 2)
    first = min((d.at for d in donations), default=datetime(2024, 1, 1))
    created = first - timedelta(days=r.randint(3, 30))
    event_at = (
        datetime.fromisoformat(fundraiser.event_day + "T09:00:00+00:00")
        if fundraiser.event_day
        else created
    )
    target = fundraiser.target
    return {
        "pageId": str(r.randint(9_000_000, 9_999_999)),
        "activityCharityCreated": fundraiser.owner == charity.name,
        "activityType": "CharityAppeal"
        if fundraiser.owner == charity.name
        else "Running",
        "activityId": str(event_ids[project.name]),
        "attribution": "",
        "eventName": project.name,
        "eventId": event_ids[project.name],
        "eventCategory": "Charity appeal"
        if fundraiser.owner == charity.name
        else "Running",
        "currencySymbol": "£",
        "currencyCode": "GBP",
        "pageShortName": slug(fundraiser.name),
        "image": {
            "caption": "",
            "url": "https://images.justgiving.com/image/default.jpg",
        },
        "imageCount": "1",
        "status": "Active",
        "owner": fundraiser.owner or charity.name,
        "ownerGuid": str(uuid.UUID(int=r.getrandbits(128))),
        "ownerProfileImageUrls": {},
        "consumerId": r.randint(60_000_000, 69_999_999),
        "title": fundraiser.name,
        "showEventDate": "True" if fundraiser.event_day else "False",
        "eventDate": _dotnet(event_at),
        "showExpiryDate": "False",
        "expiryDate": _dotnet(created + timedelta(days=1_095)),
        "fundraisingTarget": str(int(target)),
        "totalRaisedPercentageOfFundraisingTarget": str(int(raised / target * 100))
        if target
        else "0",
        "totalRaisedOffline": "0",
        "totalRaisedOnline": str(raised),
        "totalRaisedSms": "0",
        "grandTotalRaisedExcludingGiftAid": str(raised),
        "donationCount": str(len(gbp)),
        "totalEstimatedGiftAid": str(gift_aid),
        "branding": {"buttonColour": None, "thermometerFillColour": None},
        "charity": {
            "id": charity_id,
            "name": charity.name,
            "description": f"{charity.name} charity",
        },
        "organisation": None,
        "media": {"images": []},
        "story": f"<p>Thank you for supporting {project.name}.</p>",
        "domain": "www.justgiving.com",
        "smsCode": None,
        "companyAppealId": 0,
        "campaignGuid": str(uuid.UUID(int=r.getrandbits(128))),
        "inMemoriam": False,
        "rememberedPersonSummary": None,
        "pageSummaryWhat": None,
        "pageSummaryWhy": None,
        "teams": [],
        "pageSummary": "",
        "pageGuid": str(uuid.UUID(int=r.getrandbits(128))),
        "pageCreatedDate": _dotnet(created),
    }


def batches(
    charity: Charity, donations: list[Donation], end: datetime, seed: int
) -> list[Batch]:
    if "justgiving" not in charity.projects:
        return []
    r = rng(seed, charity.org_id, "justgiving-format")
    charity_id = r.randint(2_000_000, 2_999_999)
    event_ids = {
        p.name: r.randint(4_000_000, 4_999_999) for p in charity.projects["justgiving"]
    }

    by_page: dict[str, list[Donation]] = {}
    pages = []
    for project in charity.projects["justgiving"]:
        for fundraiser in project.fundraisers:
            own = [d for d in donations if d.fundraiser is fundraiser]
            by_page[slug(fundraiser.name)] = own
            pages.append(
                shape_page_details(
                    _page_body(
                        charity, charity_id, event_ids, fundraiser, project, own, r
                    )
                )
                | {"_page_short_name": slug(fundraiser.name)}
            )

    first_pull, second_pull = [], []
    for page, own in by_page.items():
        for d in own:
            record = _donation_record(d, charity_id, r) | {"_page_short_name": page}
            first_pull.append(record)
            if not d.refunded:
                second_pull.append(record)

    return [
        Batch("raw_justgiving_pages", pages, ingested_at=end),
        Batch(
            "raw_justgiving_donations",
            first_pull,
            ingested_at=end - timedelta(days=1),
            phase=1,
        ),
        Batch("raw_justgiving_donations", second_pull, ingested_at=end, phase=2),
    ]
