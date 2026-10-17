with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_list_activity_daily') }}

),

renamed as (

    select
        list_id,
        cast(day as date) as activity_date,
        subs as new_subscribers,
        unsubs as unsubscribes,
        other_adds,
        other_removes,
        emails_sent,
        unique_opens,
        recipient_clicks,
        hard_bounce as hard_bounces,
        soft_bounce as soft_bounces,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
