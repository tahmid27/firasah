"""Wipe and rebuild the synthetic dataset: generate raw data for the three
demo charities, load it through the real loader, build dbt into the
`synthetic` target, and set up one demo login per charity.

Usage: uv run python -m synthetic.load [--seed 42] [--skip-supabase] [--keep-marts]
"""

import argparse
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from ingestion.common import load_raw_to_bigquery, raw_table_id, update_env_file
from synthetic.charities import CHARITIES
from synthetic.generate import generate

DATASET = "firasah_synthetic"
LOCATION = "europe-west2"
OUT_DIR = Path("data/synthetic")
# The job image has dbt on its PATH and no uv, so the command is configurable
DBT = os.environ.get("FIRASAH_DBT", "uv run dbt").split()
DBT_ARGS = [
    "--target",
    "synthetic",
    "--project-dir",
    "dbt",
    "--profiles-dir",
    str(Path(os.environ.get("DBT_PROFILES_DIR", "~/.dbt")).expanduser()),
]


# Dashboard tables the API reads. A nightly refresh keeps these in place until
# dbt rebuilds them, so the live demo never goes empty while data reloads.
MART_PREFIXES = ("fct_", "dim_")


def tables_to_delete(names: list[str], keep_marts: bool) -> list[str]:
    if not keep_marts:
        return names
    return [n for n in names if not n.startswith(MART_PREFIXES)]


def reset_dataset(
    client: bigquery.Client, dataset: str, keep_marts: bool = False
) -> None:
    if not dataset.endswith("_synthetic"):
        raise SystemExit(f"refusing to wipe {dataset!r}: not a synthetic dataset")
    ref = f"{client.project}.{dataset}"
    try:
        client.get_dataset(ref)
    except NotFound:
        target = bigquery.Dataset(ref)
        target.location = LOCATION
        client.create_dataset(target)
    tables = {t.table_id: t.reference for t in client.list_tables(ref)}
    for name in tables_to_delete(list(tables), keep_marts):
        client.delete_table(tables[name])
    kept = "dashboard tables kept" if keep_marts else "empty"
    print(f"[synthetic] {ref} reset ({kept})")


def dbt(command: str, *extra: str) -> None:
    result = subprocess.run(
        [*DBT, command, *extra, *DBT_ARGS], check=False, capture_output=True, text=True
    )
    summary = [
        line
        for line in result.stdout.splitlines()
        if "Done." in line or "ERROR" in line or "WARN" in line
    ]
    print(
        f"[synthetic] dbt {command}: "
        + (summary[-1].strip() if summary else "no summary")
    )
    if result.returncode != 0:
        print(result.stdout[-3000:])
        raise SystemExit(f"dbt {command} failed")


def load(batch, org_id: str) -> None:
    load_raw_to_bigquery.fn(
        batch.rows,
        raw_table_id(batch.table, DATASET),
        batch.tags,
        org_id=org_id,
        schema=batch.schema,
        ingested_at=batch.ingested_at,
        row_ingested_at=batch.row_ingested_at,
    )


def demo_logins() -> None:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    upsert = {**headers, "Prefer": "resolution=merge-duplicates"}
    for c in CHARITIES:
        httpx.post(
            f"{url}/rest/v1/organisations?on_conflict=id",
            headers=upsert,
            json={"id": c.org_id, "name": c.name},
        ).raise_for_status()
        env_key = f"FIRASAH_{c.org_id.upper()}"
        if not os.environ.get(f"{env_key}_USER_ID"):
            # Demo accounts see only synthetic data, so an easy-to-type
            # password (the account name) is fine: demo-small / demo-small
            name = c.org_id.replace("_", "-")
            email, password = f"{name}@example.com", name
            response = httpx.post(
                f"{url}/auth/v1/admin/users",
                headers=headers,
                json={"email": email, "password": password, "email_confirm": True},
            )
            response.raise_for_status()
            update_env_file(
                {
                    f"{env_key}_EMAIL": email,
                    f"{env_key}_PASSWORD": password,
                    f"{env_key}_USER_ID": response.json()["id"],
                }
            )
            load_dotenv(override=True)
        httpx.post(
            f"{url}/rest/v1/memberships?on_conflict=user_id",
            headers=upsert,
            json={
                "user_id": os.environ[f"{env_key}_USER_ID"],
                "org_id": c.org_id,
                "role": "admin",
            },
        ).raise_for_status()
        print(f"[synthetic] demo login ready for {c.name} ({c.org_id})")


def data_end_date(now: datetime) -> date:
    """The last day the demo data covers.

    Today from 07:00 UTC, yesterday before that. (When no pull time is given the
    generator stamps its latest pull at 06:00 UTC on this day, so 07:00 is the
    first moment that stamp is safely in the past.)
    """
    today = now.date()
    return today if now.hour >= 7 else today - timedelta(days=1)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-supabase", action="store_true")
    parser.add_argument(
        "--keep-marts",
        action="store_true",
        help="leave the dashboard tables in place until dbt rebuilds them",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="the first pull is already loaded: continue from the first snapshot",
    )
    args = parser.parse_args()

    now = datetime.now(UTC)
    end = data_end_date(now)
    # Stamp the latest pull with the real time of this run, so "latest data" is
    # only old when no run has happened, not whenever a run is late.
    pulled_at = now.replace(second=0, microsecond=0)
    generated = [
        generate(c, end, args.seed, OUT_DIR, pulled_at=pulled_at) for c in CHARITIES
    ]
    for g in generated:
        print(
            f"[synthetic] {g.charity.name}: {g.donations:,} donations, {g.posts:,} posts, {g.emails} emails"
        )

    client = bigquery.Client()
    if not args.resume:
        reset_dataset(client, DATASET, keep_marts=args.keep_marts)
    for phase in (1, 2):
        if phase == 2 or not args.resume:
            for g in generated:
                for batch in g.batches:
                    if batch.phase == phase:
                        load(batch, g.charity.org_id)
        if phase == 1:
            # A fresh dataset has no staging views yet, and the snapshot reads one
            dbt("run", "--select", "staging")
        dbt("snapshot")
    dbt("run")
    dbt("test")

    if not args.skip_supabase:
        demo_logins()
    print(f"[synthetic] done: {client.project}.{DATASET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
