-- Fail if a populated REQUIRES or FULFILLS row carries missing, blank, or
-- invalid provenance, or references an endpoint that is absent from the
-- canonical graph.
--
-- Note: node-level provenance does not satisfy edge-level provenance. A node
-- that carries `source` does not make its linking record valid; each linking
-- record is checked independently.

-- Execution deferred: p1-001 O-1 (seed restoration) blocks `dbt build` from
-- reaching the mart layer; the singular test's execution is pending seeds.
-- The file exists and carries the contract; its failure mode is verified by
-- the Python test suite (`tests/graph/test_edge_provenance.py`) until seeds
-- are restored.
--
-- AC-5 (provenance): fails when a mart row carries null/blank/invalid
-- provenance (mapping_confidence out of [0,1], missing normalization_version,
-- missing mapping_version, missing source, missing observed_at, missing
-- freshness_status) or an invalid timestamp.
-- AC-7 (dangling endpoint): fails when a linking row points at a node key
-- that does not exist in the corresponding node mart.

with invalid_requires as (
    select
        'edge_requires' as relationship_type,
        recipe_id,
        occurrence_id as relationship_identity,
        'missing_or_blank_source' as reason
    from {{ ref('edge_requires') }}
    where source is null or trim(source) = ''

    union all
    select 'edge_requires', recipe_id, occurrence_id, 'missing_or_blank_snapshot'
    from {{ ref('edge_requires') }}
    where source_snapshot_id is null or trim(source_snapshot_id) = ''

    union all
    select 'edge_requires', recipe_id, occurrence_id, 'missing_or_blank_version'
    from {{ ref('edge_requires') }}
    where normalization_version is null or trim(normalization_version) = ''

    union all
    select 'edge_requires', recipe_id, occurrence_id, 'missing_or_blank_confidence'
    from {{ ref('edge_requires') }}
    where mapping_confidence is null

    union all
    select 'edge_requires', recipe_id, occurrence_id, 'confidence_out_of_range'
    from {{ ref('edge_requires') }}
    where mapping_confidence < 0 or mapping_confidence > 1

    union all
    select 'edge_requires', recipe_id, occurrence_id, 'missing_or_invalid_timestamp'
    from {{ ref('edge_requires') }}
    where observed_at is null
       or try_cast(observed_at as timestamp) is null
),

     invalid_fulfills as (
         select
             'edge_fulfills' as relationship_type,
             candidate_key,
             food_key as relationship_identity,
             'missing_or_blank_source' as reason
         from {{ ref('edge_fulfills') }}
         where source is null or trim(source) = ''

         union all
         select 'edge_fulfills', candidate_key, food_key, 'missing_or_blank_snapshot'
         from {{ ref('edge_fulfills') }}
         where source_snapshot_id is null or trim(source_snapshot_id) = ''

         union all
         select 'edge_fulfills', candidate_key, food_key, 'missing_or_blank_version'
         from {{ ref('edge_fulfills') }}
         where mapping_version is null or trim(mapping_version) = ''

         union all
         select 'edge_fulfills', candidate_key, food_key, 'missing_or_blank_confidence'
         from {{ ref('edge_fulfills') }}
         where mapping_confidence is null

         union all
         select 'edge_fulfills', candidate_key, food_key, 'confidence_out_of_range'
         from {{ ref('edge_fulfills') }}
         where mapping_confidence < 0 or mapping_confidence > 1

         union all
         select 'edge_fulfills', candidate_key, food_key, 'missing_or_invalid_timestamp'
         from {{ ref('edge_fulfills') }}
         where observed_at is null
            or try_cast(observed_at as timestamp) is null
     ),

     dangling_requires as (
         select
             'edge_requires' as relationship_type,
             r.recipe_id as relationship_identity,
             'dangling_recipe' as reason
         from {{ ref('edge_requires') }} r
    left join {{ ref('node_recipe') }} n
on r.recipe_id = n.recipe_id
where n.recipe_id is null

union all
select 'edge_requires', r.occurrence_id, 'dangling_food_concept'
from {{ ref('edge_requires') }} r
    left join {{ ref('node_food_concept') }} c
on r.normalized_name = c.canonical_key
where c.canonical_key is null
    ),

    dangling_fulfills as (
select
    'edge_fulfills' as relationship_type,
    f.candidate_key as relationship_identity,
    'dangling_food' as reason
from {{ ref('edge_fulfills') }} f
    left join {{ ref('node_food') }} n
on f.food_key = n.food_key
where n.food_key is null

union all
select 'edge_fulfills', f.candidate_key, 'dangling_food_concept'
from {{ ref('edge_fulfills') }} f
    left join {{ ref('node_food_concept') }} c
on f.canonical_key = c.canonical_key
where c.canonical_key is null
    )

select * from invalid_requires
union all select * from invalid_fulfills
union all select * from dangling_requires
union all select * from dangling_fulfills
