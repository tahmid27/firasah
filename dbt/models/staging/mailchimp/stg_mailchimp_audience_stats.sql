with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_audience_stats') }}

),

renamed as (

    select
        id as list_id,
        name as list_name,
        date_created,
        visibility,
        -- nested under `stats`, same dot-notation approach as the
        -- campaign reports model
        stats.member_count as member_count,
        stats.unsubscribe_count as unsubscribe_count,
        stats.campaign_count as campaign_count,
        stats.open_rate as avg_open_rate,
        stats.click_rate as avg_click_rate,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
