-- Raw badges lack product resolution, issuer, scope, and validity required for approval.
select
    cast(null as varchar) as product_key, cast(null as varchar) as diet_key,
    cast(null as varchar) as status, cast(null as varchar) as evidence_ref,
    cast(null as varchar) as evidence_kind, cast(null as varchar) as issuer,
    cast(null as timestamp) as assessed_at, cast(null as timestamp) as expires_at,
    cast(null as varchar) as policy_version
where false
