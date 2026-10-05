{{ config(enabled=var('enable_coverage_report', false)) }}

with expected(dimension) as (
    values
        ('nutrition_coverage'),
        ('price_availability'),
        ('package_unit_conversion_coverage'),
        ('dietary_evidence_coverage'),
        ('whole_recipe_completeness')
), report as (
    select * from {{ ref('coverage_quality_report') }}
), duplicate_dimensions as (
    select dimension, 'duplicate dimension' as violation
    from report
    group by dimension
    having count(*) <> 1
), missing_dimensions as (
    select e.dimension, 'missing dimension' as violation
    from expected e
    left join report r using (dimension)
    where r.dimension is null
), invalid_metrics as (
    select dimension, 'invalid metric bounds' as violation
    from report
    where covered_count < 0
       or denominator < 0
       or covered_count > denominator
       or percentage < 0
       or percentage > 1
       or (denominator = 0 and percentage is not null)
       or (denominator > 0 and percentage <> covered_count::double / denominator)
), invalid_population as (
    select dimension, 'invalid population denominator' as violation
    from report
    where dimension <> 'whole_recipe_completeness'
      and denominator <> (select count(*) from {{ ref('edge_requires') }})
    union all
    select dimension, 'invalid recipe denominator' as violation
    from report
    where dimension = 'whole_recipe_completeness'
      and denominator <> (select count(distinct recipe_id) from {{ ref('node_recipe') }})
)
select * from duplicate_dimensions
union all select * from missing_dimensions
union all select * from invalid_metrics
union all select * from invalid_population
