-- One row per account *per ingestion run* across every social platform
-- (TikTok + Instagram) — deliberately NOT deduplicated to one row per
-- account, unlike fct_social_posts. Each pull is a genuine point-in-time
-- data point (follower count on this date vs. that date), which is what
-- makes a "follower growth over time" chart possible; collapsing to the
-- latest row would throw that history away.
select * from {{ ref('int_social_account_stats_unioned') }}
