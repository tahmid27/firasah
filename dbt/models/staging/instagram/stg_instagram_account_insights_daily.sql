with raw as (

    select * from {{ source('instagram', 'raw_instagram_account_insights_daily') }}

),

renamed as (

    select
        _org_id as org_id,
        _ig_user_id as account_id,
        date as insight_date,
        reach,
        views as view_count,
        accounts_engaged,
        likes as like_count,
        comments as comment_count,
        shares as share_count,
        saves as save_count,
        reposts as repost_count,
        total_interactions,
        profile_links_taps,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
