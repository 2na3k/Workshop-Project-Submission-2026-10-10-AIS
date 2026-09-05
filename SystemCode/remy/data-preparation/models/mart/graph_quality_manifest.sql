with counts as (
    select 'node' as entity_type, 'Recipe' as entity, count(*)::bigint as row_count, 14000::bigint as allocation from {{ ref('node_recipe') }}
    union all select 'node', 'FoodConcept', count(*), 35000 from {{ ref('node_food_concept') }}
    union all select 'node', 'Food', count(*), 32000 from {{ ref('node_food') }}
    union all select 'node', 'Product', count(*), 6000 from {{ ref('node_product') }}
    union all select 'node', 'Offer', count(*), 6000 from {{ ref('node_offer') }}
    union all select 'node', 'Component', count(*), 3200 from {{ ref('node_component') }}
    union all select 'node', 'Allergen', count(*), 16 from {{ ref('node_allergen') }}
    union all select 'node', 'Diet', count(*), 4 from {{ ref('node_diet') }}
    union all select 'relationship', 'REQUIRES', count(*), 155000 from {{ ref('edge_requires') }}
    union all select 'relationship', 'FOOD_FULFILLS', count(*), 50000 from {{ ref('edge_fulfills') }}
    union all select 'relationship', 'PRODUCT_FULFILLS', count(*), 18000 from {{ ref('edge_product_fulfills') }}
    union all select 'relationship', 'USES_NUTRITION', count(*), 6000 from {{ ref('edge_uses_nutrition') }}
    union all select 'relationship', 'HAS_OFFER', count(*), 6000 from {{ ref('edge_has_offer') }}
    union all select 'relationship', 'ALLERGEN_STATUS', count(*), 96000 from {{ ref('edge_allergen_status') }}
    union all select 'relationship', 'DIET_STATUS', count(*), 24000 from {{ ref('edge_diet_status') }}
    union all select 'relationship', 'HAS_COMPONENT', count(*), 3200 from {{ ref('edge_has_component') }}
), totals as (
    select entity_type, sum(row_count)::bigint as row_count,
        case when entity_type = 'node' then 96220 else 358200 end::bigint as allocation
    from counts group by entity_type
)
select entity_type, entity, row_count, allocation, row_count <= allocation as within_allocation,
    false as strict_planning_ready,
    'missing accepted product fulfillment/profile, verified current offers, safety evidence, quantities/conversions/yields' as capability_reason
from counts
union all
select entity_type, concat('TOTAL_', upper(entity_type)), row_count, allocation, row_count <= allocation,
    false, 'available-data projection only'
from totals
