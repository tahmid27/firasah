with raw as (

    select * from {{ source('launchgood', 'raw_launchgood_donations') }}

),

renamed as (

    select
        safe_cast(donation_id as int64) as donation_id,
        safe_cast(created_date_utc as timestamp) as donation_date,
        created_time_utc as donation_time,
        status,
        transaction_type,
        offline_or_online_donation = 'online' as is_online,
        donation_currency_dc as currency_code,
        -- CSV-sourced columns land as empty strings for a blank cell, not
        -- SQL null (unlike JustGiving's JSON API, where a missing field is
        -- a real null) — cast() errors on '', so every numeric/timestamp
        -- cast here uses safe_cast instead, which returns null for '' too.
        safe_cast(donation_amount_in_donation_currency as numeric) as amount,
        campaign_name,
        campaign_url,
        community_name,
        community_url,
        project_impact_location,
        first_name as donor_first_name,
        last_name as donor_last_name,
        display_name as donor_display_name,
        email as donor_email,
        anonymous_or_public as donor_visibility,
        gift_aid_yes_or_no as is_gift_aid,
        zakat_yes_or_no as is_zakat,
        safe_cast(zakat_amount_in_donation_currency as numeric) as zakat_amount,
        source as traffic_source,
        payment_type,
        safe_cast(total_processing_fees_paid_by_cc_in_settled_currency as numeric) as processing_fees,
        safe_cast(total_online_donations_net_amount_in_settled_currency as numeric) as net_amount,
        settlement_currency,
        marketing_consent as has_marketing_consent,
        _source_file as source_file,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
