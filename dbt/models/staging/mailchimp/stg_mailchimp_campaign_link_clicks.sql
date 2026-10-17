with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_campaign_link_clicks') }}

),

renamed as (

    select
        campaign_id,
        id as link_id,
        url,
        total_clicks,
        unique_clicks,
        click_percentage,
        unique_click_percentage,
        last_click as last_clicked_at,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
