"""A batch of raw rows bound for one raw table, as the connectors would land it."""

from dataclasses import dataclass, field
from datetime import datetime

from google.cloud import bigquery


@dataclass
class Batch:
    table: str
    rows: list[dict]
    ingested_at: datetime | None = None
    row_ingested_at: list[datetime] | None = None
    tags: dict = field(default_factory=dict)
    schema: list[bigquery.SchemaField] | None = None
    # 1 = before the first snapshot run, 2 = the second pull (refunds removed)
    phase: int = 1
