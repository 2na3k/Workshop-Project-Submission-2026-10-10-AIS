with facts as (
    select
        c.canonical_key,
        c.status,
        count(distinct f.food_key) as food_count,
        count(distinct p.product_key) as product_count
    from {{ ref('node_food_concept') }} c
    left join {{ ref('edge_fulfills') }} f using (canonical_key)
    left join {{ ref('edge_product_fulfills') }} p using (canonical_key)
    group by c.canonical_key, c.status
)
select canonical_key
from facts
where (status = 'purchasable_candidate' and product_count = 0)
   or (status = 'nutrition_only' and (food_count = 0 or product_count > 0))
   or (status = 'unmatched' and (food_count > 0 or product_count > 0))
