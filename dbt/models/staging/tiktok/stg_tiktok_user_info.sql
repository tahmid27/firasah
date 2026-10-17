with raw as (

    select * from {{ source('tiktok', 'raw_tiktok_user_info') }}

),

renamed as (

    select
        _org_id as org_id,
        open_id as account_id,
        display_name,
        follower_count,
        following_count,
        likes_count,
        video_count,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
