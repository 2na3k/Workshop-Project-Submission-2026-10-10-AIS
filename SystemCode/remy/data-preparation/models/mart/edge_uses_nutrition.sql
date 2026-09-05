-- The aggregate mapped profiles do not retain auditable Product-to-Food links.
select
    cast(null as varchar) as product_key, cast(null as varchar) as food_key,
    cast(null as varchar) as method, cast(null as double) as confidence,
    cast(null as varchar) as approval_status, cast(null as boolean) as state_compatible,
    cast(null as boolean) as basis_compatible, cast(null as varchar) as source,
    cast(null as varchar) as mapping_version
where false
