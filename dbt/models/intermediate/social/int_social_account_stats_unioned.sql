with tiktok as (

    select
        org_id,
        'tiktok' as platform,
        cast(account_id as string) as source_account_id,
        display_name,
        follower_count,
        following_count,
        video_count as post_count,
        likes_count as total_likes,
        ingested_at

    from {{ ref('stg_tiktok_user_info') }}

),

instagram as (

    select
        org_id,
        'instagram' as platform,
        cast(account_id as string) as source_account_id,
        name as display_name,
        followers_count as follower_count,
        follows_count as following_count,
        media_count as post_count,
        -- Instagram's basic account fields don't expose a lifetime
        -- total-likes figure the way TikTok's user.info does
        cast(null as int64) as total_likes,
        ingested_at

    from {{ ref('stg_instagram_account_info') }}

),

unioned as (

    select * from tiktok
    union all
    select * from instagram

)

select
    concat(platform, '-', source_account_id) as account_id,
    org_id,
    platform,
    display_name,
    follower_count,
    following_count,
    post_count,
    total_likes,
    ingested_at

from unioned
