with requirements as (
    select distinct normalized_name as canonical_key
    from {{ ref('edge_requires') }}
    group by normalized_name
), fulfillment_status as (
    select canonical_key, count(*) as fulfillment_count
    from {{ ref('edge_fulfills') }}
    group by canonical_key
)
select
    r.canonical_key,
    r.canonical_key as name,
    case when coalesce(f.fulfillment_count, 0) > 0 then 'matched' else 'unmatched' end as status,
    'recipe-food-v2' as normalization_version
from requirements r
left join fulfillment_status f using (canonical_key)
