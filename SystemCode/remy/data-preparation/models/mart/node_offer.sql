-- Supplied listings have no currency, observation time, availability, or current-slot evidence.
select
    cast(null as varchar) as offer_key,
    cast(null as varchar) as retailer,
    cast(null as varchar) as market,
    cast(null as varchar) as channel,
    cast(null as varchar) as currency,
    cast(null as bigint) as package_price_minor,
    cast(null as double) as price_per_100g,
    cast(null as double) as price_per_100ml,
    cast(null as timestamp) as observed_at,
    cast(null as timestamp) as expires_at,
    cast(null as varchar) as availability,
    cast(null as varchar) as price_status,
    cast(null as varchar) as source_url
where false
