-- One row per campaign, ready to chart. Deduplicated to the latest-known
-- version of each campaign — open/click counts keep accumulating for a
-- while after a campaign sends, so a later pull's figures supersede an
-- earlier one's, same reasoning as fct_social_posts.
select *
from {{ ref('stg_mailchimp_campaign_reports') }}
qualify row_number() over (partition by campaign_id order by ingested_at desc) = 1
