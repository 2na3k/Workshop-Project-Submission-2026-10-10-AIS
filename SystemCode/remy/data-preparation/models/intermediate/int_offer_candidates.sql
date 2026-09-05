select
    i.product_key,
    l.source_row_id,
    l.raw_price,
    cast(round(l.raw_price * 100) as bigint) as package_price_minor,
    cast(null as varchar) as currency,
    cast(null as timestamp) as observed_at,
    cast(null as timestamp) as expires_at,
    'unknown' as availability,
    'unknown' as price_status,
    'missing_currency_timestamp_availability' as unavailable_reason
from {{ ref('stg_retail_listing') }} l
join {{ ref('int_product_identity') }} i using (source_row_id)
where l.raw_price > 0
