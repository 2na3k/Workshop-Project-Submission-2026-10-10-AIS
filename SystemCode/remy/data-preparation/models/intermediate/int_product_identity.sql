with normalized as (
    select
        *,
        lower(trim(regexp_replace(coalesce(name, ''), '[^a-zA-Z0-9]+', ' ', 'g'))) as normalized_name,
        lower(trim(regexp_replace(coalesce(quantity_raw, ''), '[^a-zA-Z0-9.]+', '', 'g'))) as normalized_pack
    from {{ ref('stg_retail_listing') }}
    where name is not null
), keyed as (
    select
        *,
        case
            when retailer_product_id is not null then concat(retailer, ':', retailer_product_id, ':', coalesce(nullif(normalized_pack, ''), 'unknown-pack'))
            else concat(retailer, ':provisional:', md5(concat_ws('|', retailer, normalized_name, normalized_pack)))
        end as product_key
    from normalized
), assessed as (
    select
        *,
        count(distinct normalized_name) over (partition by product_key) as identity_name_count,
        row_number() over (partition by product_key order by source_kind = 'search' desc, source_row_id) as identity_rank
    from keyed
)
select
    product_key,
    retailer_product_id,
    retailer,
    name,
    brand,
    quantity_raw,
    try_cast(regexp_extract(lower(quantity_raw), '([0-9]+(?:\.[0-9]+)?)\s*(kg|g)\b', 1) as double)
      * case when regexp_extract(lower(quantity_raw), '([0-9]+(?:\.[0-9]+)?)\s*(kg|g)\b', 2) = 'kg' then 1000 else 1 end as package_mass_g,
    try_cast(regexp_extract(lower(quantity_raw), '([0-9]+(?:\.[0-9]+)?)\s*(l|ml)\b', 1) as double)
      * case when regexp_extract(lower(quantity_raw), '([0-9]+(?:\.[0-9]+)?)\s*(l|ml)\b', 2) = 'l' then 1000 else 1 end as package_volume_ml,
    try_cast(regexp_extract(lower(quantity_raw), '^\s*([0-9]+)\s*(?:x|pcs?|pieces?|pack)\b', 1) as bigint) as package_count,
    cast(null as double) as edible_fraction,
    regexp_extract(lower(name), '\b(raw|cooked|dry|hydrated|frozen|whole|ground|salted|unsalted)\b', 1) as food_state,
    case
        when identity_name_count > 1 then 'conflict'
        when retailer_product_id is not null then 'verified_id'
        else 'provisional'
    end as identity_status,
    case
        when lower(coalesce(category, '')) similar to '%(household|electronics)%'
          or regexp_matches(lower(name), '\b(lotion|shampoo|detergent|cleaner|toothpaste)\b')
          then 'rejected_non_food'
        else 'review_required'
    end as food_classification_status,
    source_snapshot_id,
    source_row_id
from assessed
where identity_rank = 1
qualify row_number() over (order by identity_status = 'verified_id' desc, product_key) <= 6000
