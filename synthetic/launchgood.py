"""LaunchGood donor-report CSV exports, parsed by the connector's own reader."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

from ingestion.launchgood_donations import read_donations_export
from synthetic.batches import Batch
from synthetic.charities import Charity
from synthetic.donations import FOREIGN, Donation
from synthetic.justgiving import slug
from synthetic.rand import rng

HEADER = json.loads((Path(__file__).parent / "reference_shapes.json").read_text())[
    "launchgood_export_csv_header"
]["columns"]
IMPACT = {"Wells": "SO", "Qurbani": "PK", "Iftar": "PS", "Zakat": "YE", "Orphan": "BD"}


def _impact(project_name: str) -> str:
    return next((code for word, code in IMPACT.items() if word in project_name), "GB")


def _row(d: Donation, charity: Charity, fake: Faker, r, end: datetime) -> dict:
    donor, gbp = d.donor, d.currency == "GBP"
    rate = 1 if gbp else FOREIGN[d.currency]
    gross = round(d.amount / rate, 2)
    fees = round(gross * 0.039 + 0.20, 2)
    settled = d.at + timedelta(days=3) < end - timedelta(days=7)
    peer = d.fundraiser.name.startswith(("Sisters", "Yusuf", "Brothers"))
    return {
        "Donation ID": d.donation_id,
        "Created Date (UTC)": d.at.strftime("%Y-%m-%d"),
        "Created Time (UTC)": d.at.strftime("%H:%M:%S"),
        "Settled Date (UTC)": (d.at + timedelta(days=3)).strftime("%Y-%m-%d")
        if settled
        else "",
        "Donation Payout Flag": "Paid Out" if settled else "Not Paid Out",
        "Transaction Type": "donation",
        "Status": "Refunded" if d.refunded else "Charged",
        "Offline or online donation": "online" if d.online else "offline",
        "First Name": donor.first,
        "Last Name": donor.last,
        "Display Name": "Anonymous"
        if donor.anonymous
        else f"{donor.first} {donor.last[0]}.",
        "Email": donor.email,
        "Marketing Consent": "yes" if donor.marketing_consent else "no",
        "Gift Aid (yes or no)": "yes" if d.is_gift_aid else "no",
        "Tax Receipt requested": "No",
        "Billing Name": f"{donor.first} {donor.last}",
        "Billing Address": fake.street_address(),
        "Billing Address 2": "",
        "Billing City": donor.city if gbp else "New York",
        "Billing State": "",
        "Billing Zip": fake.postcode() if gbp else "10001",
        "Billing Country": "GB" if gbp else "US",
        "Anonymous or Public": "Anonymous Donor" if donor.anonymous else "Public Donor",
        "Donation Currency (DC)": d.currency,
        "Donation Amount (in Donation Currency)": d.amount,
        "Project Currency": "GBP",
        "Donation Amount in Project Currency (May be approx.)": gross,
        "Settlement Currency": "GBP",
        "Total Online Donation Gross Amount in Settled Currency": gross,
        "Total Processing Fees Paid by CC In Settled Currency": fees,
        "Total Online Donations Net Amount in Settled Currency": round(gross - fees, 2),
        "Transfer ID": f"TR{r.randint(100_000, 999_999)}" if settled else "",
        "Zakat (yes or no)": "yes" if d.is_zakat else "no",
        "Zakat Amount (in Donation Currency)": d.amount if d.is_zakat else "",
        "Has Giving Level": "No",
        "Giving Level Title": "",
        "Giving Level Description": "",
        "Giving Level Type": "",
        "Giving Level Qty": "",
        "Giving Level Notes": "",
        "Giving Level Email": "",
        "Giving Level Fund Code": "",
        "Giving Level Campaign Code": "",
        "Shipping Name": "",
        "Shipping Address": "",
        "Shipping Address 2": "",
        "Shipping City": "",
        "Shipping State": "",
        "Shipping Zip": "",
        "Shipping Country": "",
        "Campaign Name": d.fundraiser.name,
        "Campaign URL": f"https://www.launchgood.com/v4/campaign/{slug(d.fundraiser.name)}",
        "Project Impact Location": _impact(d.project.name),
        "Community Name": d.project.name,
        "Community URL": f"https://www.launchgood.com/communitypage/{slug(d.project.name)}",
        "Source": d.traffic_source,
        "Source User Profile": f"https://www.launchgood.com/user/{donor.donor_id}"
        if peer
        else "",
        "Number of Donors": 1,
        "Comments": d.message,
        "Email (for tax receipt)": donor.email if d.is_gift_aid else "",
        "Payment Type": r.choice(
            ("credit card", "credit card", "apple pay", "paypal", "google pay")
        ),
    }


def batches(
    charity: Charity, donations: list[Donation], end: datetime, out_dir: Path, seed: int
) -> list[Batch]:
    if "launchgood" not in charity.projects:
        return []
    r = rng(seed, charity.org_id, "launchgood-format")
    fake = Faker("en_GB")
    fake.seed_instance(r.getrandbits(32))
    rows = sorted(
        (_row(d, charity, fake, r, end) for d in donations),
        key=lambda x: x["Donation ID"],
    )
    cutoff = (end - timedelta(days=180)).strftime("%Y-%m-%d")

    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    # An older export, and a newer one that overlaps it (re-exports happen)
    for name, selected, arrived in (
        (
            "launchgood_export_older.csv",
            [x for x in rows if x["Created Date (UTC)"] <= cutoff],
            end - timedelta(days=180),
        ),
        ("launchgood_export.csv", rows, end),
    ):
        path = out_dir / name
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(selected)
        result.append(
            Batch(
                "raw_launchgood_donations",
                read_donations_export.fn(path),
                ingested_at=arrived,
                tags={"_source_file": name},
            )
        )
    return result
