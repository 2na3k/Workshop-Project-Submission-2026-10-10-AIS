select canonical_key
from {{ ref('edge_fulfills') }}
group by canonical_key
having count(*) > 50
