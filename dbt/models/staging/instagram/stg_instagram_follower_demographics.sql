with raw as (

    select * from {{ source('instagram', 'raw_instagram_follower_demographics') }}

),

renamed as (

    select
        _ig_user_id as account_id,
        breakdown as breakdown_type,
        bucket as breakdown_value,
        followers as follower_count,
        _ingested_at as ingested_at
    from raw

)

select * from renamed
