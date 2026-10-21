{{ config(
    enabled=var('enable_coverage_report', false),
    materialized='table',
    tags=['coverage_report']
) }}

{% set assoc_snapshot = env_var("REMY_SOURCE_SNAPSHOT_ID", "") %}
{% set assoc_checksum = env_var("REMY_MART_CONTENT_CHECKSUM", "") %}
{% set assoc_build = env_var("REMY_BUILD_ID", "") %}
with requirements as (
    select
        occurrence_id as requirement_id,
        recipe_id,
        normalized_name as canonical_key
    from {{ ref('edge_requires') }}
), recipes as (
    select distinct recipe_id
    from {{ ref('node_recipe') }}
), candidate_capabilities as (
    select
        r.requirement_id,
        r.recipe_id,
        r.canonical_key,
        coalesce(nf.nutrition_status, 'missing') = 'validated' as nutrition_covered,
        coalesce(f.price_status, 'unavailable') = 'estimated' as price_covered,
        coalesce(f.cost_basis_compatible, false) as conversion_covered,
        (
            f.halal_status in ('certified', 'retailer_claim', 'ingredient_screen_pass')
            or f.vegetarian_status in ('retailer_claim', 'ingredient_screen_pass')
        ) as dietary_covered
    from requirements r
    left join {{ ref('edge_fulfills') }} f
        on f.canonical_key = r.canonical_key
    left join {{ ref('node_food') }} nf
        on nf.food_key = f.food_key
), requirement_flags as (
    select
        requirement_id,
        recipe_id,
        max(cast(nutrition_covered as integer)) = 1 as nutrition_covered,
        max(cast(price_covered as integer)) = 1 as price_covered,
        max(cast(conversion_covered as integer)) = 1 as conversion_covered,
        max(cast(dietary_covered as integer)) = 1 as dietary_covered
    from candidate_capabilities
    group by requirement_id, recipe_id
), recipe_flags as (
    select
        r.recipe_id,
        count(rf.requirement_id) > 0
            and bool_and(
                rf.nutrition_covered
                and rf.price_covered
                and rf.conversion_covered
                and rf.dietary_covered
            ) as complete
    from recipes r
    left join requirement_flags rf using (recipe_id)
    group by r.recipe_id
), metrics as (
    select
        'nutrition_coverage' as dimension,
        count(*) filter (where nutrition_covered)::bigint as covered_count,
        count(*)::bigint as denominator
    from requirement_flags
    union all
    select
        'price_availability',
        count(*) filter (where price_covered)::bigint,
        count(*)::bigint
    from requirement_flags
    union all
    select
        'package_unit_conversion_coverage',
        count(*) filter (where conversion_covered)::bigint,
        count(*)::bigint
    from requirement_flags
    union all
    select
        'dietary_evidence_coverage',
        count(*) filter (where dietary_covered)::bigint,
        count(*)::bigint
    from requirement_flags
    union all
    select
        'whole_recipe_completeness',
        count(*) filter (where complete)::bigint,
        count(*)::bigint
    from recipe_flags
), associated as (
    select
        dimension,
        covered_count,
        denominator,
        case when denominator = 0 then null else covered_count::double / denominator end as percentage,
        case when denominator = 0 then 'no_population' else 'computed' end as population_status,
        '{{ assoc_snapshot }}' as source_snapshot_id,
        '{{ assoc_checksum }}' as mart_content_checksum,
        '{{ assoc_build }}' as build_id,
        '{{ run_started_at }}'::timestamp as observed_at
    from metrics
), validated as (
    select case
        when '{{ assoc_snapshot }}' = ''
          or '{{ assoc_checksum }}' = ''
          or '{{ assoc_build }}' = ''
        then error('coverage_quality_report failed closed: build association is not configured')
        when count(*) <> 5
          or count(distinct dimension) <> 5
          or count(*) filter (where dimension not in (
                'nutrition_coverage',
                'price_availability',
                'package_unit_conversion_coverage',
                'dietary_evidence_coverage',
                'whole_recipe_completeness'
            )) > 0
          or bool_or(covered_count < 0)
          or bool_or(denominator < 0)
          or bool_or(covered_count > denominator)
          or bool_or(percentage is not null and (percentage < 0 or percentage > 1))
          or bool_or(denominator = 0 and percentage is not null)
          or bool_or(denominator > 0 and percentage is null)
        then error('coverage_quality_report failed closed: invalid metrics')
        else true
    end as valid
    from associated
)
select a.*
from associated a
cross join validated v
where v.valid
