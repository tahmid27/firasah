-- Who an account's followers are, split by age band, gender, country or
-- city. One row per bucket per ingestion run — deliberately NOT
-- deduplicated: each pull is a point-in-time snapshot, and the history is
-- what shows the audience shifting. Filter to the latest ingested_at for
-- "the audience right now". Instagram only for now.
select
    concat('instagram-', cast(account_id as string)) as account_id,
    org_id,
    'instagram' as platform,
    breakdown_type,
    breakdown_value,
    follower_count,
    ingested_at

from {{ ref('stg_instagram_follower_demographics') }}
