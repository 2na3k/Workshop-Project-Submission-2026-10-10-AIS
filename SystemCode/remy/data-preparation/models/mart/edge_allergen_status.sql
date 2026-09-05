-- Missing allergen declarations are unknown, never free-from evidence.
select
    cast(null as varchar) as product_key, cast(null as varchar) as allergen_key,
    cast(null as varchar) as status, cast(null as varchar) as evidence_ref,
    cast(null as varchar) as evidence_kind, cast(null as timestamp) as assessed_at,
    cast(null as timestamp) as expires_at, cast(null as varchar) as policy_version
where false
