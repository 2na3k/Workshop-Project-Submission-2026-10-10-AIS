with source_rows as (
    select
        try_cast(column0 as bigint) as recipe_id,
        Ingredients as raw_value,
        Cleaned_Ingredients as cleaned_value,
        {{ recipe_nonempty_list_items('Cleaned_Ingredients') }} as cleaned_items,
        {{ recipe_nonempty_list_items('Ingredients') }} as raw_items
    from {{ ref('stg_recipes') }}
    where try_cast(column0 as bigint) is not null
), raw_rows as (
    select
        recipe_id,
        {{ recipe_unquote('item') }} as raw_text,
        position
    from source_rows, unnest(raw_items) with ordinality as items(item, position)
), cleaned_rows as (
    select
        recipe_id,
        {{ recipe_unquote('item') }} as cleaned_text,
        position
    from source_rows, unnest(cleaned_items) with ordinality as items(item, position)
), occurrences as (
    select
        s.recipe_id,
        s.position,
        r.raw_text,
        coalesce(nullif(s.cleaned_text, ''), r.raw_text) as cleaned_text
    from cleaned_rows s
    left join raw_rows r using (recipe_id, position)
    union all
    select
        r.recipe_id,
        r.position,
        r.raw_text,
        r.raw_text as cleaned_text
    from raw_rows r
    where not exists (
        select 1 from cleaned_rows s where s.recipe_id = r.recipe_id
    )
), effective as (
    select
        *,
        coalesce(nullif(cleaned_text, ''), raw_text) as effective_text
    from occurrences
    where coalesce(nullif(cleaned_text, ''), raw_text) is not null
), normalized as (
    select
        *,
        {{ recipe_normalize('effective_text') }} as normalized_name,
        lower(regexp_extract(effective_text, '^\\s*[0-9./¼½¾⅓⅔⅛⅜⅝⅞ ]+([A-Za-z]+)', 1)) as extracted_unit
    from effective
), parsed as (
    select
        *,
        case extracted_unit
            when 'tsp' then 'teaspoon'
            when 'tsps' then 'teaspoon'
            when 'teaspoon' then 'teaspoon'
            when 'teaspoons' then 'teaspoon'
            when 'tbsp' then 'tablespoon'
            when 'tbsps' then 'tablespoon'
            when 'tablespoon' then 'tablespoon'
            when 'tablespoons' then 'tablespoon'
            when 'cup' then 'cup'
            when 'cups' then 'cup'
            when 'lb' then 'pound'
            when 'lbs' then 'pound'
            when 'pound' then 'pound'
            when 'pounds' then 'pound'
            when 'oz' then 'ounce'
            when 'ounce' then 'ounce'
            when 'ounces' then 'ounce'
            when 'g' then 'gram'
            when 'gram' then 'gram'
            when 'grams' then 'gram'
            when 'kg' then 'kilogram'
            when 'ml' then 'milliliter'
            when 'l' then 'liter'
            when 'clove' then 'clove'
            when 'cloves' then 'clove'
            when 'can' then 'can'
            when 'cans' then 'can'
            when 'package' then 'package'
            when 'packages' then 'package'
            when 'pinch' then 'pinch'
            when 'piece' then 'piece'
            when 'pieces' then 'piece'
            when 'quart' then 'quart'
            when 'quarts' then 'quart'
            else null
        end as unit
    from normalized
)
select
    recipe_id,
    concat(cast(recipe_id as varchar), ':', cast(position - 1 as varchar)) as occurrence_id,
    cast(position - 1 as integer) as position,
    coalesce(raw_text, cleaned_text) as raw_text,
    cleaned_text,
    normalized_name,
    try_cast(regexp_extract(effective_text, '^\\s*([0-9]+(?:\\.[0-9]+)?)', 1) as double) as quantity,
    unit,
    nullif(regexp_extract(effective_text, '(?i)\\b(chopped|diced|sliced|minced|peeled|seeded|grated|crushed|drained|rinsed|halved|beaten|melted|torn)\\b', 1), '') as preparation,
    'josephrmartinez/recipe-dataset' as source
from parsed
where normalized_name is not null
  and normalized_name <> ''
  and normalized_name not in ('a', 'an', 'the', 'and', 'or', 'of', 'to', 'for', 'as', 'in')
