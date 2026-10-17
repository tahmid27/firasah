-- One row per link per campaign: which links in each email were clicked,
-- and how often. Deduplicated to the latest pull — click counts keep
-- growing for a while after a send, so a later pull supersedes an earlier
-- one (same reasoning as fct_mailchimp_campaigns).
select
    concat(campaign_id, '-', link_id) as link_click_id,
    org_id,
    campaign_id,
    link_id,
    url,
    total_clicks,
    unique_clicks,
    click_percentage,
    unique_click_percentage,
    last_clicked_at,
    ingested_at

from {{ ref('stg_mailchimp_campaign_link_clicks') }}
qualify row_number() over (partition by org_id, campaign_id, link_id order by ingested_at desc) = 1
