with failures as (
    select 'mapped_profile_count' as failure
    from {{ ref('stg_price_mapped_nutrients') }} having count(*) <> 10845
    union all
    select 'retail_listing_count'
    from {{ ref('stg_retail_listing') }} having count(*) <> 5211
    union all
    select 'invalid_nutrient'
    from {{ ref('stg_price_mapped_nutrients') }}
    where least(protein_g, fat_g, carbohydrate_g, energy_kcal, fiber_g, sodium_mg, saturated_fat_g, sugars_g, cholesterol_mg) < 0
    union all
    select 'unsafe_food_fulfillment'
    from {{ ref('edge_fulfills') }}
    where approval_status <> 'accepted' or match_method in ('ingredient_text_only', 'strong_fuzzy_name')
       or (match_method = 'rule_based_substitution' and rule_id is null)
    union all
    select 'fabricated_product_fulfillment'
    from {{ ref('edge_product_fulfills') }}
    union all
    select 'fabricated_product_nutrition'
    from {{ ref('edge_uses_nutrition') }}
    union all
    select 'fabricated_current_offer'
    from {{ ref('node_offer') }}
    union all
    select 'fabricated_allergen_assessment'
    from {{ ref('edge_allergen_status') }}
    union all
    select 'fabricated_diet_assessment'
    from {{ ref('edge_diet_status') }}
    union all
    select 'graph_allocation_exceeded'
    from {{ ref('graph_quality_manifest') }} where not within_allocation
)
select * from failures
