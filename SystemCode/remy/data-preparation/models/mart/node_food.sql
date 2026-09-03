with selected_ids as (
    select distinct try_cast(regexp_replace(food_key, '^fdc:', '') as bigint) as fdc_id
    from {{ ref('edge_fulfills') }}
    where food_key is not null
    union
    select distinct try_cast(fdc_id as bigint)
    from {{ ref('stg_food_component') }}
    where fdc_id is not null
), food as (
    select *
    from {{ ref('stg_food') }}
    qualify row_number() over (partition by try_cast(fdc_id as bigint) order by try_cast(fdc_id as bigint)) = 1
), branded as (
    select *
    from {{ ref('stg_branded_food') }}
    qualify row_number() over (partition by try_cast(fdc_id as bigint) order by modified_date desc nulls last) = 1
), nutrient_rows as (
    select
        try_cast(fdc_id as bigint) as fdc_id,
        try_cast(nutrient_id as bigint) as nutrient_id,
        try_cast(amount as double) as amount,
        row_number() over (
            partition by try_cast(fdc_id as bigint), try_cast(nutrient_id as bigint)
            order by amount is null, try_cast(id as bigint) desc nulls last
        ) as row_num
    from {{ ref('stg_food_nutrient') }}
    where try_cast(nutrient_id as bigint) in (1003, 1004, 1005, 1008, 1079, 1093, 1258, 1063, 2000)
), nutrients as (
    select
        fdc_id,
        max(amount) filter (where nutrient_id = 1008) as energy_kcal,
        max(amount) filter (where nutrient_id = 1003) as protein_g,
        max(amount) filter (where nutrient_id = 1004) as fat_g,
        max(amount) filter (where nutrient_id = 1258) as saturated_fat_g,
        max(amount) filter (where nutrient_id = 1005) as carbohydrate_g,
        max(amount) filter (where nutrient_id = 1079) as fiber_g,
        coalesce(
            max(amount) filter (where nutrient_id = 2000),
            max(amount) filter (where nutrient_id = 1063)
        ) as sugars_g,
        max(amount) filter (where nutrient_id = 1093) as sodium_mg
    from nutrient_rows
    where row_num = 1
    group by fdc_id
)
select
    s.fdc_id,
    concat('fdc:', cast(s.fdc_id as varchar)) as food_key,
    f.description,
    f.data_type,
    b.brand_name,
    b.brand_owner,
    b.ingredients,
    try_cast(b.serving_size as double) as serving_size,
    b.serving_size_unit,
    b.household_serving_fulltext,
    b.package_weight,
    n.energy_kcal,
    n.protein_g,
    n.fat_g,
    n.saturated_fat_g,
    n.carbohydrate_g,
    n.fiber_g,
    n.sugars_g,
    n.sodium_mg,
    'fooddata_central' as source
from selected_ids s
left join food f using (fdc_id)
left join branded b using (fdc_id)
left join nutrients n using (fdc_id)
where s.fdc_id is not null
