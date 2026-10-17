"""Email endpoints (fct_mailchimp_*)."""

from typing import Annotated

from fastapi import APIRouter, Query

from api.data import Warehouse
from api.schemas import CampaignRow, CampaignScorecard

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/campaigns", response_model=CampaignScorecard)
def campaigns(wh: Warehouse, limit: Annotated[int, Query(ge=1, le=200)] = 50):
    rows = wh.fetch(
        "fct_mailchimp_campaigns",
        [
            "campaign_id",
            "campaign_title",
            "subject_line",
            "send_time",
            "emails_sent",
            "unique_opens",
            "open_rate",
            "unique_clicks",
            "click_rate",
            "unsubscribe_count",
            "hard_bounces",
            "soft_bounces",
        ],
        order_by=[("send_time", "desc")],
        limit=limit,
    )
    return CampaignScorecard(
        rows=[
            CampaignRow(
                campaign_id=row["campaign_id"],
                campaign_title=row["campaign_title"],
                subject_line=row["subject_line"],
                send_time=row["send_time"],
                emails_sent=row["emails_sent"],
                unique_opens=row["unique_opens"],
                open_rate=row["open_rate"],
                unique_clicks=row["unique_clicks"],
                click_rate=row["click_rate"],
                click_to_open_rate=(
                    round(row["unique_clicks"] / row["unique_opens"], 4)
                    if row["unique_opens"]
                    else None
                ),
                unsubscribes=row["unsubscribe_count"],
                bounces=(row["hard_bounces"] or 0) + (row["soft_bounces"] or 0),
            )
            for row in rows
        ]
    )
