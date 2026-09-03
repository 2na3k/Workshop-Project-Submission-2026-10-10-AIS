with concepts as (
    select distinct normalized_name as canonical_key
    from {{ ref('edge_requires') }}
), 
food_source as (
    select try_cast(fdc_id as bigint) as fdc_id, data_type, description
    from {{ ref('stg_food') }}
    where try_cast(fdc_id as bigint) is not null
), 
normalized_food as (
    select
        *,
        {{ recipe_normalize('description', false) }} as base_name,
        {{ recipe_normalize('description') }} as canonical_key
    from food_source
    where description is not null
), 
direct_candidates as (
    select
        f.fdc_id,
        concat('fdc:', cast(f.fdc_id as varchar)) as food_key,
        c.canonical_key,
        'direct' as kind,
        case when f.base_name <> f.canonical_key then 0.95 else 1.0 end as confidence,
        case when f.base_name <> f.canonical_key then 'approved_alias' else 'exact_normalized_description' end as match_method,
        cast(null as varchar) as context,
        cast(null as varchar) as ratio,
        'recipe_food_to_dbt:v2' as source
    from normalized_food f
    join concepts c on c.canonical_key = f.canonical_key
    where f.canonical_key <> ''
), 
fuzzy_candidates as (
    select
        f.fdc_id,
        concat('fdc:', cast(f.fdc_id as varchar)) as food_key,
        c.canonical_key,
        'direct' as kind,
        0.85 as confidence,
        'strong_fuzzy_name' as match_method,
        cast(null as varchar) as context,
        cast(null as varchar) as ratio,
        'recipe_food_to_dbt:v2' as source
    from normalized_food f
    join concepts c
      on split_part(f.canonical_key, ' ', 1) = split_part(c.canonical_key, ' ', 1)
    where f.canonical_key <> ''
      and f.canonical_key <> c.canonical_key
      and abs(length(f.canonical_key) - length(c.canonical_key)) <= 4
      and 1.0 - levenshtein(f.canonical_key, c.canonical_key)::double
          / greatest(length(f.canonical_key), length(c.canonical_key), 1) >= 0.85
), branded_parts as (
    select
        try_cast(b.fdc_id as bigint) as fdc_id,
        trim(part) as part
    from {{ ref('stg_branded_food') }} b,
         unnest(regexp_split_to_array(coalesce(b.ingredients, ''), '[,;]')) as ingredients(part)
    where try_cast(b.fdc_id as bigint) is not null
), ingredient_candidates as (
    select distinct
        p.fdc_id,
        concat('fdc:', cast(p.fdc_id as varchar)) as food_key,
        c.canonical_key,
        'direct' as kind,
        0.60 as confidence,
        'ingredient_text_only' as match_method,
        cast(null as varchar) as context,
        cast(null as varchar) as ratio,
        'recipe_food_to_dbt:v2' as source
    from branded_parts p
    join concepts c on c.canonical_key = {{ recipe_normalize('p.part') }}
), substitution_rules(target_key, replacement_key, context, ratio) as (
    values
        ('chicken broth', 'vegetable broth', 'vegetarian', '1:1'),
        ('beef broth', 'vegetable broth', 'vegetarian', '1:1'),
        ('butter', 'olive oil', 'dairy_free', '3:4'),
        ('milk', 'soy milk', 'dairy_free', '1:1'),
        ('egg', 'flax egg', 'vegan_baking', '1:1')
), substitution_candidates as (
    select
        f.fdc_id,
        concat('fdc:', cast(f.fdc_id as varchar)) as food_key,
        r.target_key as canonical_key,
        'substitute' as kind,
        0.95 as confidence,
        'rule_based_substitution' as match_method,
        r.context,
        r.ratio,
        'recipe_food_to_dbt:v2' as source
    from normalized_food f
    join substitution_rules r on r.replacement_key = f.canonical_key
    join concepts c on c.canonical_key = r.target_key
), candidates as (
    select * from direct_candidates
    union all
    select * from fuzzy_candidates
    union all
    select * from ingredient_candidates
    union all
    select * from substitution_candidates
), deduplicated as (
    select *
    from candidates
    qualify row_number() over (
        partition by food_key, canonical_key, kind
        order by confidence desc, fdc_id
    ) = 1
), 
ranked as (
    select
        *,
        row_number() over (
            partition by canonical_key, kind
            order by confidence desc, fdc_id
        ) as kind_rank,
        count(*) filter (where kind = 'substitute') over (partition by canonical_key) as substitute_count
    from deduplicated
), 
capped as (
    select *
    from ranked
    where (kind = 'substitute' and kind_rank <= 5)
       or (kind = 'direct' and kind_rank <= greatest(0, 50 - least(5, substitute_count)))
)
select
    food_key,
    canonical_key,
    kind,
    confidence,
    match_method,
    context,
    ratio,
    source
from capped
