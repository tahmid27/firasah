with tiktok as (

    select
        'tiktok' as platform,
        cast(video_id as string) as source_post_id,
        posted_at,
        description as caption,
        'VIDEO' as media_type,
        share_url as permalink,
        view_count,
        like_count,
        comment_count,
        share_count,
        ingested_at

    from {{ ref('stg_tiktok_videos') }}
    qualify row_number() over (partition by video_id order by ingested_at desc) = 1

),

instagram as (

    select
        'instagram' as platform,
        cast(media_id as string) as source_post_id,
        posted_at,
        caption,
        media_type,
        permalink,
        -- Instagram's basic media fields don't expose view counts the way
        -- TikTok's video.list does — would need the separate insights
        -- endpoint (instagram_manage_insights, already granted) for that,
        -- not pulled in yet
        cast(null as int64) as view_count,
        like_count,
        comments_count as comment_count,
        cast(null as int64) as share_count,
        ingested_at

    from {{ ref('stg_instagram_media') }}
    qualify row_number() over (partition by media_id order by ingested_at desc) = 1

),

unioned as (

    select * from tiktok
    union all
    select * from instagram

)

select
    -- source_post_id alone isn't unique across platforms, same reasoning
    -- as fct_donations.donation_id
    concat(platform, '-', source_post_id) as post_id,
    platform,
    posted_at,
    caption,
    media_type,
    permalink,
    view_count,
    like_count,
    comment_count,
    share_count,
    ingested_at

from unioned
