"""The data access endpoints receive: a warehouse bound to the caller's org."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends

from api.settings import Settings, get_settings
from api.tenancy import CurrentOrg
from api.warehouse import Filter, QueryExecutor, SelectItem, get_executor, query_mart


@dataclass(frozen=True)
class TenantWarehouse:
    ctx: CurrentOrg
    executor: QueryExecutor
    settings: Settings

    def fetch(
        self,
        mart: str,
        columns: Sequence[SelectItem],
        *,
        filters: Sequence[Filter] = (),
        order_by: Sequence[tuple[str, str]] = (),
        limit: int | None = None,
    ) -> list[dict]:
        return query_mart(
            self.ctx,
            mart,
            columns,
            executor=self.executor,
            settings=self.settings,
            filters=filters,
            order_by=order_by,
            limit=limit,
        )


def get_tenant_warehouse(
    ctx: CurrentOrg,
    executor: Annotated[QueryExecutor, Depends(get_executor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TenantWarehouse:
    return TenantWarehouse(ctx=ctx, executor=executor, settings=settings)


def get_today() -> date:
    return datetime.now(UTC).date()


Warehouse = Annotated[TenantWarehouse, Depends(get_tenant_warehouse)]
Today = Annotated[date, Depends(get_today)]
