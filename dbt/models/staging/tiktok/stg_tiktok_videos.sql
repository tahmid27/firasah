with raw as (

    select * from {{ source('tiktok', 'raw_tiktok_videos') }}

),

renamed as (

    select
        _org_id as org_id,
        id as video_id,
        title,
        video_description as description,
        cover_image_url,
        share_url,
        duration as duration_seconds,
        -- create_time arrives as a Unix epoch (seconds), not a timestamp string
        timestamp_seconds(create_time) as posted_at,
        view_count,
        like_count,
        comment_count,
        share_count,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
