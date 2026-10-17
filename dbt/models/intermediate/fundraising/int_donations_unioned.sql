with latest_justgiving_pages as (

    -- stg_justgiving_pages is one row per page per pull (target and
    -- running totals change), so take the latest row per page
    select *
    from {{ ref('stg_justgiving_pages') }}
    qualify row_number() over (partition by org_id, page_short_name order by ingested_at desc) = 1

),

justgiving as (

    select
        d.org_id,
        'justgiving' as source,
        cast(d.donation_id as string) as source_donation_id,
        d.donation_date,
        d.amount,
        d.currency_code,
        d.donor_name,
        -- JustGiving donations belong to an individual fundraising page;
        -- the larger event/appeal the page sits under comes from the page
        -- details pull
        coalesce(p.page_title, d.page_short_name) as fundraiser_name,
        p.event_name as project_name,
        d.traffic_source,
        cast(null as bool) as is_online,
        coalesce(
            d.donor_name is null or lower(trim(d.donor_name)) in ('', 'anonymous'),
            true
        ) as is_anonymous,
        cast(null as bool) as is_gift_aid,
        cast(null as bool) as is_zakat,
        -- JustGiving's donations endpoint doesn't expose any of these —
        -- left as explicit nulls rather than dropping the columns, so
        -- LaunchGood's richer detail still reaches the mart
        cast(null as numeric) as zakat_amount,
        cast(null as numeric) as processing_fees,
        cast(null as numeric) as net_amount,
        cast(null as string) as settlement_currency,
        cast(null as bool) as has_marketing_consent

    -- Refund-aware: only donations still present as of the last snapshot
    -- run. See justgiving_donations_snapshot for how that's detected.
    from {{ ref('justgiving_donations_snapshot') }} as d
    -- Joined on org_id too: a page's details must come from the same
    -- charity's pull, never another tenant's copy of the same page
    left join latest_justgiving_pages as p
        on d.org_id = p.org_id
        and d.page_short_name = p.page_short_name
    where d.dbt_valid_to is null

),

launchgood as (

    select
        org_id,
        'launchgood' as source,
        cast(donation_id as string) as source_donation_id,
        donation_date,
        amount,
        currency_code,
        donor_display_name as donor_name,
        -- LaunchGood's campaign_name is the individual fundraiser page;
        -- community_name is the larger project it belongs to
        campaign_name as fundraiser_name,
        community_name as project_name,
        traffic_source,
        is_online,
        coalesce(
            donor_visibility = 'Anonymous Donor'
                or donor_display_name is null
                or lower(trim(donor_display_name)) in ('', 'anonymous'),
            true
        ) as is_anonymous,
        is_gift_aid,
        is_zakat,
        zakat_amount,
        processing_fees,
        net_amount,
        settlement_currency,
        has_marketing_consent

    -- No refund/cancellation detection on this side yet. A JustGiving-style
    -- snapshot (comparing consecutive pulls to spot a vanished donation)
    -- isn't reliable here: each CSV export is a manual, one-off dump, not a
    -- live re-queryable API, so a donation can "disappear" between two
    -- exports just because the second one covered a different date range,
    -- not because it was refunded — that would produce false invalidations,
    -- worse than no detection at all. Revisit once a real export is seen
    -- containing a refunded donation: the raw `status` field (not carried
    -- into stg_launchgood_donations as a filter yet) may flag it directly,
    -- which would be a plain filter, no snapshot needed.
    --
    -- Still deduped to the latest-ingested row per donation_id, same as
    -- JustGiving's snapshot source query does internally — the raw layer
    -- is append-only, so re-ingesting the same (or an overlapping) CSV
    -- export would otherwise produce duplicate rows here and break the
    -- unique test on fct_donations.donation_id.
    from {{ ref('stg_launchgood_donations') }}
    qualify row_number() over (partition by org_id, donation_id order by ingested_at desc) = 1

),

unioned as (

    select * from justgiving
    union all
    select * from launchgood

)

select
    -- source_donation_id alone isn't unique across platforms (JustGiving
    -- and LaunchGood both hand out their own small integer IDs
    -- independently), so the two are combined into one cross-platform key
    concat(source, '-', source_donation_id) as donation_id,
    org_id,
    source,
    donation_date,
    amount,
    currency_code,
    -- A missing or placeholder name means an anonymous donor, not bad data
    if(is_anonymous, 'Anonymous', donor_name) as donor_name,
    is_anonymous,
    fundraiser_name,
    project_name,
    traffic_source,
    is_online,
    is_gift_aid,
    is_zakat,
    zakat_amount,
    processing_fees,
    net_amount,
    settlement_currency,
    has_marketing_consent

from unioned
