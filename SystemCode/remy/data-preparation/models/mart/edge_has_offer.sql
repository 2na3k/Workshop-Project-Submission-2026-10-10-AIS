-- Undated, currency-less listing prices cannot identify a current Offer slot.
select cast(null as varchar) as product_key, cast(null as varchar) as offer_key
where false
