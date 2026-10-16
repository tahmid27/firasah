-- One row per audience/list *per ingestion run* — deliberately NOT
-- deduplicated, same reasoning as fct_social_account_stats. Each pull is a
-- genuine point-in-time data point (subscriber count on this date vs. that
-- date), which is what makes an audience-growth-over-time chart possible.
select * from {{ ref('stg_mailchimp_audience_stats') }}
