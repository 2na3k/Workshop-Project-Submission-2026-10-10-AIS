with source(value) as (
    values ($$['', 'onion']$$)
), actual as (
    select
        {{ recipe_unquote('item') }} as item,
        position
    from source,
         unnest({{ recipe_nonempty_list_items('value') }}) with ordinality as items(item, position)
), expected(position, item) as (
    values (1, 'onion')
)
select e.position, e.item
from expected e
left join actual a using (position)
where a.position is null or a.item <> e.item
