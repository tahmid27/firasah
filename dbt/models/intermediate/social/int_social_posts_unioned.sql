with tiktok as (

    select
        org_id,
        'tiktok' as platform,
        cast(video_id as string) as source_post_id,
        posted_at,
        description as caption,
        'VIDEO' as media_type,
        -- Instagram-only distinction (Reels vs feed); not applicable to TikTok
        cast(null as string) as media_product_type,
        share_url as permalink,
        view_count,
        like_count,
        comment_count,
        share_count,
        cast(null as int64) as save_count,
        cast(null as int64) as reach,
        cast(null as int64) as repost_count,
        cast(null as int64) as profile_visits,
        cast(null as int64) as new_follower_count,
        cast(null as float64) as avg_watch_time_seconds,
        cast(null as float64) as skip_rate,
        ingested_at

    from {{ ref('stg_tiktok_videos') }}
    qualify row_number() over (partition by org_id, video_id order by ingested_at desc) = 1

),

instagram as (

    select
        m.org_id,
        'instagram' as platform,
        cast(m.media_id as string) as source_post_id,
        m.posted_at,
        m.caption,
        m.media_type,
        m.media_product_type,
        m.permalink,
        -- Insights come from a separate endpoint, joined on the post.
        -- Views are only meaningful for video/Reels: old image and
        -- carousel posts report 0, meaning "not measured", so views are
        -- nulled for them rather than showing a misleading zero. Reach is
        -- the metric that works across every format.
        if(m.media_type = 'VIDEO', i.view_count, null) as view_count,
        m.like_count,
        m.comments_count as comment_count,
        i.share_count,
        i.save_count,
        i.reach,
        i.repost_count,
        i.profile_visits,
        i.new_follower_count,
        -- Reels only; null for feed posts
        i.avg_watch_time_seconds,
        i.skip_rate,
        m.ingested_at

    from {{ ref('stg_instagram_media') }} as m
    -- Left join: posts from before the account became a business account
    -- have no insights, and must still appear
    left join (
        select *
        from {{ ref('stg_instagram_media_insights') }}
        qualify row_number() over (partition by org_id, media_id order by ingested_at desc) = 1
    ) as i
        on m.org_id = i.org_id
        and m.media_id = i.media_id
    qualify row_number() over (partition by m.org_id, m.media_id order by m.ingested_at desc) = 1

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
    org_id,
    platform,
    posted_at,
    caption,
    media_type,
    media_product_type,
    permalink,
    view_count,
    like_count,
    comment_count,
    share_count,
    save_count,
    reach,
    repost_count,
    profile_visits,
    new_follower_count,
    avg_watch_time_seconds,
    skip_rate,
    ingested_at

from unioned
