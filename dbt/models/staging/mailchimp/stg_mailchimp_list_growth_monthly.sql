with raw as (

    select * from {{ source('mailchimp', 'raw_mailchimp_list_growth_monthly') }}

),

renamed as (

    select
        _org_id as org_id,
        list_id,
        -- Mailchimp sends the month as text like "2026-09"
        parse_date('%Y-%m-%d', concat(month, '-01')) as month_start,
        existing as existing_subscribers,
        imports as imported_subscribers,
        optins as opt_in_subscribers,
        subscribed,
        unsubscribed,
        reconfirm,
        cleaned,
        pending,
        deleted,
        transactional,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
