with requirements as (
    select distinct normalized_name as canonical_key
    from {{ ref('edge_requires') }}
), food_fulfillment as (
    select distinct canonical_key
    from {{ ref('edge_fulfills') }}
    where approval_status = 'accepted'
), product_fulfillment as (
    select distinct canonical_key
    from {{ ref('edge_product_fulfills') }}
    where approval_status = 'accepted'
)
select
    r.canonical_key,
    r.canonical_key as name,
    case
        when p.canonical_key is not null then 'purchasable_candidate'
        when f.canonical_key is not null then 'nutrition_only'
        else 'unmatched'
    end as status,
    'recipe-food-v3' as normalization_version
from requirements r
left join food_fulfillment f using (canonical_key)
left join product_fulfillment p using (canonical_key)
