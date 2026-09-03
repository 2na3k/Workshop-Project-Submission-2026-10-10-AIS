select c.canonical_key
from {{ ref('node_food_concept') }} c
left join {{ ref('edge_fulfills') }} f using (canonical_key)
group by c.canonical_key, c.status
having (c.status = 'matched' and count(f.food_key) = 0)
    or (c.status = 'unmatched' and count(f.food_key) > 0)
