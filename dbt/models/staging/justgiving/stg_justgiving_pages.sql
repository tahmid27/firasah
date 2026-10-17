with raw as (

    select * from {{ source('justgiving', 'raw_justgiving_pages') }}

),

renamed as (

    select
        _page_short_name as page_short_name,
        pageGuid as page_guid,
        title as page_title,
        owner as owner_name,
        status as page_status,
        activityType as activity_type,
        eventId as event_id,
        eventName as event_name,
        campaignGuid as campaign_guid,
        charity.id as charity_id,
        charity.name as charity_name,
        currencyCode as currency_code,
        safe_cast(fundraisingTarget as numeric) as fundraising_target,
        safe_cast(grandTotalRaisedExcludingGiftAid as numeric) as total_raised,
        safe_cast(totalEstimatedGiftAid as numeric) as total_estimated_gift_aid,
        safe_cast(donationCount as int64) as donation_count,
        timestamp_millis(cast(regexp_extract(pageCreatedDate, r'\d+') as int64)) as page_created_at,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
