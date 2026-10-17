with raw as (

    select * from {{ source('instagram', 'raw_instagram_media_insights') }}

),

renamed as (

    select
        _org_id as org_id,
        media_id,
        _ig_user_id as account_id,
        reach,
        views as view_count,
        shares as share_count,
        saved as save_count,
        total_interactions,
        reposts as repost_count,
        profile_visits,
        follows as new_follower_count,
        ig_reels_avg_watch_time / 1000 as avg_watch_time_seconds,
        ig_reels_video_view_total_time / 1000 as total_watch_time_seconds,
        reels_skip_rate as skip_rate,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
