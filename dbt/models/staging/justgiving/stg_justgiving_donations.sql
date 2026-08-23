with source as (

    select * from {{ ref('justgiving_donations') }}

),

renamed as (

    select
        donation_id,
        donor_full_name as donor_name,
        cast(donation_amount_gbp as numeric) as amount_gbp,
        cast(donation_date as date) as donation_date,
        campaign as campaign_name,
        payment_method,
        cast(is_gift_aid as boolean) as is_gift_aid

    from source

)

select * from renamed
