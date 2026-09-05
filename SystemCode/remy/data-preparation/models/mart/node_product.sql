select
    product_key,
    retailer_product_id,
    retailer,
    name,
    brand,
    cast(null as varchar) as product_url,
    quantity_raw,
    package_mass_g,
    package_volume_ml,
    package_count,
    edible_fraction,
    food_state,
    cast(null as varchar) as ingredients_raw,
    identity_status,
    food_classification_status,
    source_snapshot_id
from {{ ref('int_product_identity') }}
where food_classification_status <> 'rejected_non_food'
