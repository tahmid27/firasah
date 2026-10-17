with raw as (

    select * from {{ source('instagram', 'raw_instagram_account_info') }}

),

renamed as (

    select
        _org_id as org_id,
        id as account_id,
        username,
        name,
        biography,
        followers_count,
        follows_count,
        media_count,
        profile_picture_url,
        _ingested_at as ingested_at

    from raw

)

select * from renamed
