"""API configuration from the environment."""

import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Interpolated into SQL as identifiers, so restricted
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    bigquery_project: str
    bigquery_dataset: str

    def __post_init__(self):
        for name in ("bigquery_project", "bigquery_dataset"):
            if not _IDENTIFIER.match(getattr(self, name)):
                raise ValueError(f"unsafe {name}: {getattr(self, name)!r}")

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        supabase_url=os.environ["SUPABASE_URL"].rstrip("/"),
        supabase_anon_key=os.environ["SUPABASE_ANON_KEY"],
        bigquery_project=os.environ["GOOGLE_CLOUD_PROJECT"],
        bigquery_dataset=os.environ.get("BIGQUERY_DATASET", "firasah_dev"),
    )
