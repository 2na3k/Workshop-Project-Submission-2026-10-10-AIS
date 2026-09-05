with concept_usage as (
    select normalized_name as canonical_key, count(*) as occurrence_count
    from {{ ref('edge_requires') }}
    group by normalized_name
), food_source as (
    select try_cast(fdc_id as bigint) as fdc_id, description
    from {{ ref('stg_food') }}
    where try_cast(fdc_id as bigint) is not null and description is not null
    qualify row_number() over (partition by try_cast(fdc_id as bigint) order by description) = 1
), normalized_food as (
    select *, {{ recipe_normalize('description', false) }} as base_name, {{ recipe_normalize('description') }} as normalized_name
    from food_source
), direct_candidates as (
    select
        f.fdc_id,
        concat('fdc:', cast(f.fdc_id as varchar)) as food_key,
        c.canonical_key,
        'direct' as kind,
        case when f.base_name <> f.normalized_name then 0.95 else 1.0 end as confidence,
        case when f.base_name <> f.normalized_name then 'approved_alias' else 'exact_normalized_description' end as match_method,
        cast(null as varchar) as context,
        1.0::double as replacement_factor,
        'same_amount' as factor_basis,
        cast(null as varchar) as required_state,
        cast(null as varchar) as rule_id,
        'accepted' as approval_status,
        'recipe_food_to_dbt:v3' as mapping_version,
        c.occurrence_count
    from normalized_food f
    join concept_usage c on c.canonical_key = f.normalized_name
    where f.normalized_name <> ''
), substitution_rules(target_key, replacement_key, context, replacement_factor, factor_basis, rule_id) as (
    values
        ('chicken broth', 'vegetable broth', 'vegetarian', 1.0, 'volume', 'sub:chicken-broth:vegetable-broth:v1'),
        ('beef broth', 'vegetable broth', 'vegetarian', 1.0, 'volume', 'sub:beef-broth:vegetable-broth:v1'),
        ('butter', 'olive oil', 'dairy_free', 0.75, 'volume', 'sub:butter:olive-oil:v1'),
        ('milk', 'soy milk', 'dairy_free', 1.0, 'volume', 'sub:milk:soy-milk:v1'),
        ('egg', 'flax egg', 'vegan_baking', 1.0, 'count', 'sub:egg:flax-egg:v1')
), substitution_candidates as (
    select
        f.fdc_id,
        concat('fdc:', cast(f.fdc_id as varchar)) as food_key,
        r.target_key as canonical_key,
        'substitute' as kind,
        0.95 as confidence,
        'rule_based_substitution' as match_method,
        r.context,
        r.replacement_factor,
        r.factor_basis,
        cast(null as varchar) as required_state,
        r.rule_id,
        'accepted' as approval_status,
        'recipe_food_to_dbt:v3' as mapping_version,
        c.occurrence_count
    from normalized_food f
    join substitution_rules r on r.replacement_key = f.normalized_name
    join concept_usage c on c.canonical_key = r.target_key
), deduplicated as (
    select * from (
        select * from direct_candidates union all select * from substitution_candidates
    )
    qualify row_number() over (
        partition by food_key, canonical_key, kind order by confidence desc, fdc_id
    ) = 1
), per_kind as (
    select *, row_number() over (
        partition by canonical_key, kind order by confidence desc, fdc_id
    ) as kind_rank
    from deduplicated
), capped as (
    select *
    from per_kind
    where (kind = 'substitute' and kind_rank <= 1) or (kind = 'direct' and kind_rank <= 4)
), globally_capped as (
    select *
    from capped
    qualify row_number() over (
        order by occurrence_count desc, canonical_key, kind = 'substitute', confidence desc, fdc_id
    ) <= 50000
)
select
    food_key, canonical_key, kind, confidence, match_method, context,
    replacement_factor, factor_basis, required_state, rule_id, approval_status,
    'fooddata_central' as source, mapping_version
from globally_capped
