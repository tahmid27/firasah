with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_campaign_reports') }}

),

renamed as (

    select
        _org_id as org_id,
        id as campaign_id,
        campaign_title,
        subject_line,
        type as campaign_type,
        send_time,
        list_id,
        list_name,
        emails_sent,
        -- nested fields land as BigQuery STRUCTs (matching Mailchimp's
        -- nested JSON response), pulled out here with dot notation rather
        -- than a cast — see CLAUDE.md for why open_rate specifically is a
        -- genuine undercount for charities with deliverability problems
        -- (junk-foldered emails that are opened but never click don't
        -- register, since the open-tracking pixel needs remote images to
        -- load, which most clients block by default in junk folders)
        opens.opens_total as opens_total,
        opens.unique_opens as unique_opens,
        opens.open_rate as open_rate,
        clicks.clicks_total as clicks_total,
        clicks.unique_clicks as unique_clicks,
        clicks.click_rate as click_rate,
        bounces.hard_bounces as hard_bounces,
        bounces.soft_bounces as soft_bounces,
        unsubscribed as unsubscribe_count,
        abuse_reports,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
