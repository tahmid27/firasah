with raw as (

    select * from {{ source('instagram', 'raw_instagram_media_insights') }}

),

renamed as (

    select
        media_id,
        _ig_user_id as account_id,
        reach,
        views as view_count,
        shares as share_count,
        saved as save_count,
        total_interactions,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
