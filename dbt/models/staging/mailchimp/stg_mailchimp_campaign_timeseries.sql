-- One row per hour of each campaign report's 24-hour timeline (unnested
-- from the report's `timeseries` array).
with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_campaign_reports') }}

),

renamed as (

    select
        raw._org_id as org_id,
        raw.id as campaign_id,
        raw.send_time,
        hour.timestamp as hour_start,
        hour.emails_sent,
        hour.unique_opens,
        hour.recipients_clicks as recipient_clicks,
        hour.proxy_excluded_unique_opens,
        raw._ingested_at as ingested_at
    from raw, unnest(raw.timeseries) as hour

)

select * from renamed
