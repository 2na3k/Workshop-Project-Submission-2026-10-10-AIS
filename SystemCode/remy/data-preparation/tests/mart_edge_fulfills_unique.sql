select food_key, canonical_key, kind
from {{ ref('edge_fulfills') }}
group by food_key, canonical_key, kind
having count(*) > 1
