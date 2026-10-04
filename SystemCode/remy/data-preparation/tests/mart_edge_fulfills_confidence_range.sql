select *
from {{ ref('edge_fulfills') }}
where mapping_confidence < 0 or mapping_confidence > 1
