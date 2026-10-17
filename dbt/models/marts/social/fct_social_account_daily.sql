-- One row per account per day, ready to chart account-level activity over
-- time (daily reach, views, engagement, link taps). Deduplicated to the
-- latest pull per day: each ingestion run re-pulls the most recent days
-- because Instagram's figures can lag up to 48 hours, so a later pull's
-- number supersedes an earlier one. Instagram only for now — TikTok's
-- current access doesn't expose daily account-level activity.
select
    concat('instagram-', cast(account_id as string)) as account_id,
    org_id,
    'instagram' as platform,
    insight_date,
    reach,
    view_count,
    accounts_engaged,
    like_count,
    comment_count,
    share_count,
    save_count,
    repost_count,
    total_interactions,
    profile_links_taps,
    ingested_at

from {{ ref('stg_instagram_account_insights_daily') }}
qualify row_number() over (partition by org_id, account_id, insight_date order by ingested_at desc) = 1
