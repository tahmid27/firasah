with raw as (

    select * from {{ source('justgiving', 'raw_justgiving_donations') }}

),

renamed as (

    select
        id as donation_id,
        donorDisplayName as donor_name,
        cast(amount as numeric) as amount,
        currencyCode as currency_code,
        cast(donorLocalAmount as numeric) as donor_local_amount,
        donorLocalCurrencyCode as donor_local_currency_code,
        -- donationDate arrives as a .NET JSON date, e.g. /Date(1720791809000+0000)/
        -- pull out the millisecond timestamp and convert to a real timestamp
        timestamp_millis(cast(regexp_extract(donationDate, r'\d+') as int64)) as donation_date,
        charityId as charity_id,
        message as donor_message,
        source as traffic_source,
        donationRef as donation_reference,
        thirdPartyReference as third_party_reference,
        _page_short_name as page_short_name,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
