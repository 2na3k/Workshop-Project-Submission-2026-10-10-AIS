with branded as (
    select try_cast(fdc_id as bigint) as fdc_id, lower(coalesce(ingredients, '')) as ingredients
    from {{ ref('stg_branded_food') }}
    qualify row_number() over (partition by try_cast(fdc_id as bigint) order by modified_date desc nulls last) = 1
), food as (
    select
        concat('fdc:', cast(try_cast(f.fdc_id as bigint) as varchar)) as food_key,
        lower(concat_ws(' ', f.description, b.ingredients)) as evidence_text
    from {{ ref('stg_food') }} f
    left join branded b on b.fdc_id = try_cast(f.fdc_id as bigint)
    where try_cast(f.fdc_id as bigint) is not null
    qualify row_number() over (partition by try_cast(f.fdc_id as bigint) order by f.description) = 1
), concern_patterns(concern, pattern) as (
    values
        ('meat', '\b(pork|beef|chicken|turkey|lamb|mutton|veal|venison|bacon|ham|prosciutto|pepperoni|sausage|lard|tallow)\b'),
        ('fish', '\b(fish|salmon|tuna|cod|anchov(?:y|ies)|sardines?|mackerel|tilapia|trout)\b'),
        ('shellfish', '\b(shrimp|prawns?|crabs?|lobsters?|crayfish|mussels?|oysters?|clams?|scallops?|squid|octopus)\b'),
        ('gelatin', '\bgelatine?\b'),
        ('animal_rennet', '\b(animal rennet|animal enzymes?)\b'),
        ('meat_stock', '\b(meat|beef|chicken|pork|fish)\s+(broth|stock)\b')
)
select
    f.food_key,
    p.concern,
    'fdc_food_text_proxy' as evidence_kind,
    f.food_key as evidence_ref,
    'vegetarian_screen:v1' as policy_version
from food f
cross join concern_patterns p
where regexp_matches(f.evidence_text, p.pattern)
