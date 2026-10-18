"""Wipe and rebuild the synthetic dataset: generate raw data for the three
demo charities, load it through the real loader, build dbt into the
`synthetic` target, and set up one demo login per charity.

Usage: uv run python -m synthetic.load [--seed 42] [--skip-supabase]
"""

import argparse
import os
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google.cloud import bigquery

from ingestion.common import load_raw_to_bigquery, raw_table_id, update_env_file
from synthetic.charities import CHARITIES
from synthetic.generate import generate

DATASET = "firasah_synthetic"
LOCATION = "europe-west2"
OUT_DIR = Path("data/synthetic")
DBT = ["uv", "run", "dbt"]
DBT_ARGS = [
    "--target",
    "synthetic",
    "--project-dir",
    "dbt",
    "--profiles-dir",
    str(Path("~/.dbt").expanduser()),
]


def reset_dataset(client: bigquery.Client, dataset: str) -> None:
    if not dataset.endswith("_synthetic"):
        raise SystemExit(f"refusing to wipe {dataset!r}: not a synthetic dataset")
    ref = f"{client.project}.{dataset}"
    target = bigquery.Dataset(ref)
    target.location = LOCATION
    client.create_dataset(target, exists_ok=True)
    for table in client.list_tables(ref):
        client.delete_table(table.reference)
    print(f"[synthetic] {ref} is empty")


def dbt(command: str) -> None:
    result = subprocess.run(
        [*DBT, command, *DBT_ARGS], check=False, capture_output=True, text=True
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
            email, password = (
                f"{c.org_id.replace('_', '-')}@example.com",
                secrets.token_urlsafe(24),
            )
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


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-supabase", action="store_true")
    args = parser.parse_args()

    end = datetime.now(UTC).date() - timedelta(days=1)
    generated = [generate(c, end, args.seed, OUT_DIR) for c in CHARITIES]
    for g in generated:
        print(
            f"[synthetic] {g.charity.name}: {g.donations:,} donations, {g.posts:,} posts, {g.emails} emails"
        )

    client = bigquery.Client()
    reset_dataset(client, DATASET)
    for phase in (1, 2):
        for g in generated:
            for batch in g.batches:
                if batch.phase == phase:
                    load(batch, g.charity.org_id)
        dbt("snapshot")
    dbt("run")
    dbt("test")

    if not args.skip_supabase:
        demo_logins()
    print(f"[synthetic] done: {client.project}.{DATASET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
