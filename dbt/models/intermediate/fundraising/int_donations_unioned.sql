with justgiving as (

    select
        'justgiving' as source,
        cast(donation_id as string) as source_donation_id,
        donation_date,
        amount,
        currency_code,
        donor_name,
        page_short_name as campaign_name,
        cast(null as bool) as is_gift_aid,
        cast(null as bool) as is_zakat

    -- Refund-aware: only donations still present as of the last snapshot
    -- run. See justgiving_donations_snapshot for how that's detected.
    from {{ ref('justgiving_donations_snapshot') }}
    where dbt_valid_to is null

),

launchgood as (

    select
        'launchgood' as source,
        cast(donation_id as string) as source_donation_id,
        donation_date,
        amount,
        currency_code,
        donor_display_name as donor_name,
        campaign_name,
        is_gift_aid,
        is_zakat

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
    from {{ ref('stg_launchgood_donations') }}

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
    source,
    donation_date,
    amount,
    currency_code,
    donor_name,
    campaign_name,
    is_gift_aid,
    is_zakat

from unioned
