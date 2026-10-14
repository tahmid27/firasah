with raw as (

    select * from {{ source('instagram', 'raw_instagram_media') }}

),

renamed as (

    select
        id as media_id,
        _ig_user_id as account_id,
        caption,
        media_type,
        media_product_type,
        permalink,
        `timestamp` as posted_at,
        like_count,
        comments_count,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
