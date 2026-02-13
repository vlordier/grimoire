# Storage Mapping — Neo4j + Qdrant

> 1:1 mapping between the [Canonical Schemas](canonical-schemas.md) and:
>
> - **Neo4j** property graph (labels, relationship types, key properties)
> - **Qdrant** payloads (points, metadata, filtering strategy)
>
> **See also:** [Qdrant Setup](qdrant-setup.md) · [Canonical Schemas](canonical-schemas.md) · [System Architecture](../architecture/system-architecture.md)

---

## Assumptions

- ULIDs/UUIDs as string IDs throughout.
- Neo4j constraints on ID uniqueness.
- Vectors live in Qdrant; structure lives in Neo4j.
- Large text blobs go to object storage keyed by ID; keep Neo4j properties small.

---

## 1. Neo4j mapping

### 1.1 Node labels

| Label | Maps to schema |
|-------|---------------|
| `:Trace` | `Trace` |
| `:Step` | `Step` |
| `:Artifact` | `Artifact` |
| `:Pattern` | `Pattern` |

### 1.2 Constraints & indexes (Cypher)

```cypher
-- Uniqueness
CREATE CONSTRAINT trace_id_unique IF NOT EXISTS
FOR (n:Trace) REQUIRE n.trace_id IS UNIQUE;

CREATE CONSTRAINT step_id_unique IF NOT EXISTS
FOR (n:Step) REQUIRE n.step_id IS UNIQUE;

CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (n:Artifact) REQUIRE n.artifact_id IS UNIQUE;

CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (n:Pattern) REQUIRE n.pattern_id IS UNIQUE;

-- Performance indexes
CREATE INDEX trace_domain IF NOT EXISTS FOR (n:Trace) ON (n.domain);
CREATE INDEX step_trace_index IF NOT EXISTS FOR (n:Step) ON (n.trace_id, n.index);
CREATE INDEX step_role IF NOT EXISTS FOR (n:Step) ON (n.role);
CREATE INDEX step_fsm IF NOT EXISTS FOR (n:Step) ON (n.fsm_id, n.fsm_state);
CREATE INDEX artifact_type IF NOT EXISTS FOR (n:Artifact) ON (n.type);
CREATE INDEX pattern_type IF NOT EXISTS FOR (n:Pattern) ON (n.type);
```

### 1.3 Node property mapping

#### `:Trace`

| Property | Source |
|----------|--------|
| `trace_id` (PK) | `Trace.trace_id` |
| `title` | `Trace.title` |
| `domain` | `Trace.domain` |
| `tags` | `Trace.tags` (list) |
| `problem` | `Trace.problem` (truncated) |
| `created_at`, `updated_at` | datetime or string |
| `provenance_source_types` | flattened from `SourceRef.source_type` |
| `provenance_source_ids` | flattened from `SourceRef.source_id` |
| `provenance_uris` | flattened list |
| `license`, `license_url`, `attribution` | from `LicenseInfo` |
| `sensitivity` | `Provenance.sensitivity` |
| `ingested_at`, `pipeline_version`, `schema_version` | `Provenance.*` |
| `danger_ambiguity/adversarial/irreversibility/institutional` | flattened from `DangerScores` |
| `outcome` | JSON string or selected scalars |
| `n_steps` | int |

#### `:Step`

| Property | Source |
|----------|--------|
| `step_id` (PK) | `Step.step_id` |
| `trace_id` (FK) | `Step.trace_id` |
| `index` | `Step.index` |
| `actor`, `role` | string |
| `text` | raw or truncated |
| `fsm_id`, `fsm_state` | string |
| `danger_*` | optional floats |
| `tool`, `tool_name`, `tool_args_json`, `tool_result_json`, `tool_error`, `latency_ms` | flattened from `ToolCall` |
| `embedding_id`, `embedding_model`, `embedding_dim`, `embedding_storage_key`, `embedding_hash` | from `EmbeddingRef` |
| `properties_json` | string or selected fields |

#### `:Artifact`

| Property | Source |
|----------|--------|
| `artifact_id` (PK) | `Artifact.artifact_id` |
| `type`, `title`, `text` | direct |
| `tags`, `domain`, `priority` | direct |
| `data_json` | serialized `Artifact.data` |
| `embedding_*` | same as Step |

#### `:Pattern`

| Property | Source |
|----------|--------|
| `pattern_id` (PK) | `Pattern.pattern_id` |
| `type`, `name`, `description` | direct |
| `applicability_json` | serialized or flattened: `fsm_id`, `allowed_states`, `domains`, `required_tags`, `forbidden_tags`, `min_danger_*`, `max_danger_*` |
| `template_json` | serialized `PatternTemplateStep` list |
| `quality_support`, `quality_avg_revision_loops`, `quality_verification_rate`, `quality_success_proxy` | from `PatternQuality` |
| `embedding_*` | same as Step |
| `created_at`, `miner_version`, `schema_version` | direct |

### 1.4 Relationship types

```text
Core structural (between :Step nodes):
  (:Step)-[:NEXT]->(:Step)
  (:Step)-[:SUPPORTS]->(:Step)
  (:Step)-[:REFUTES]->(:Step)
  (:Step)-[:REVISES]->(:Step)
  (:Step)-[:DEPENDS_ON]->(:Step|:Artifact)

Step → Artifact links:
  (:Step)-[:MENTIONS]->(:Artifact)
  (:Step)-[:EVIDENCE_FOR]->(:Artifact)
  (:Step)-[:DECISION_FOR]->(:Artifact)
  (:Step)-[:USES_TOOL]->(:Step|:Artifact)
  (:Step)-[:CREATES]->(:Artifact)
  (:Step)-[:USES]->(:Artifact)

Trace containment:
  (:Trace)-[:HAS_STEP]->(:Step)
  (:Trace)-[:HAS_ARTIFACT]->(:Artifact)

Patterns:
  (:Step)-[:INSTANCE_OF {instance_id, bindings_json, success_proxy}]->(:Pattern)
```

All relationships can carry: `edge_id`, `weight`, `label`, `data_json`.

### 1.5 Minimal ingestion Cypher

```cypher
-- Create a Trace
MERGE (t:Trace {trace_id: $trace_id})
SET t += $trace_props;

-- Create Steps
UNWIND $steps AS s
MERGE (st:Step {step_id: s.step_id})
SET st += s.props
MERGE (t:Trace {trace_id: s.trace_id})
MERGE (t)-[:HAS_STEP]->(st);

-- Sequence edges
UNWIND $next_edges AS e
MATCH (a:Step {step_id: e.src}), (b:Step {step_id: e.dst})
MERGE (a)-[r:NEXT]->(b)
SET r += e.props;

-- Artifacts
UNWIND $artifacts AS a
MERGE (ar:Artifact {artifact_id: a.artifact_id})
SET ar += a.props
MERGE (t:Trace {trace_id: a.trace_id})
MERGE (t)-[:HAS_ARTIFACT]->(ar);

-- Mentions
UNWIND $mentions AS m
MATCH (st:Step {step_id: m.step_id}), (ar:Artifact {artifact_id: m.artifact_id})
MERGE (st)-[r:MENTIONS]->(ar)
SET r += m.props;
```

---

## 2. Qdrant payload mapping

**Principle:** Qdrant stores vectors and filterable metadata; Neo4j stores structure.

### Collections

| Collection | Granularity | Use |
|------------|-------------|-----|
| `steps` | One vector per Step | Step-level semantic retrieval |
| `step_windows` | One vector per k-step window | Procedural similarity (best index) |
| `patterns` | One vector per Pattern prototype | Pattern recommendation |

### 2.1 `steps` collection payload

```json
{
  "step_id": "01J...STEP",
  "trace_id": "01J...TRACE",
  "index": 12,
  "actor": "assistant",
  "role": "plan",
  "fsm_id": "fsm_design_decide",
  "fsm_state": "S3_plan",
  "domain": "ml",
  "tags": ["rag", "retrieval", "graph"],
  "danger_ambiguity": 0.12,
  "danger_adversarial": 0.03,
  "danger_irreversibility": 0.08,
  "danger_institutional": 0.22,
  "has_tool_call": false,
  "tool": null,
  "created_at": "2026-02-12T10:00:00Z",
  "source_type": ["huggingface"],
  "source_id": ["open-thoughts/OpenThoughts-114k"],
  "license": "cc-by",
  "sensitivity": "public"
}
```

### 2.2 `step_windows` collection payload

```json
{
  "window_id": "01J...TRACE:10:5",
  "trace_id": "01J...TRACE",
  "start_index": 10,
  "k": 5,
  "step_ids": ["...", "..."],
  "fsm_id": "fsm_diagnose_fix",
  "fsm_state": "S6_evaluate",
  "domain": "software",
  "tags": ["debugging"],
  "danger_ambiguity": 0.20,
  "danger_adversarial": 0.00,
  "danger_irreversibility": 0.10,
  "danger_institutional": 0.05,
  "has_tool_call": true,
  "license": "mit",
  "sensitivity": "public"
}
```

### 2.3 `patterns` collection payload

```json
{
  "pattern_id": "01J...PATTERN",
  "type": "fsm_subpath",
  "name": "Hypothesis → discriminating test → update belief",
  "fsm_id": "fsm_diagnose_fix",
  "allowed_states": ["S2_model", "S3_plan", "S4_execute", "S5_observe", "S6_evaluate"],
  "domains": ["software", "ml"],
  "required_tags": ["debug"],
  "forbidden_tags": [],
  "min_danger_ambiguity": null,
  "max_danger_irreversibility": 0.8,
  "quality_support": 1420,
  "quality_success_proxy": 0.71,
  "miner_version": "miner_v3",
  "schema_version": "v1"
}
```

### 2.4 Filtering strategy

When retrieving next-step patterns, filter by:

1. **FSM compatibility:** `patterns.fsm_id == current_fsm_id` AND `current_state in patterns.allowed_states`
2. **Danger constraints:** If irreversibility dominant, prefer patterns whose `max_danger_irreversibility >= current_score` or that include verification gates
3. **Domain / tags:** `domain in patterns.domains`, `required_tags ⊆ current_tags`, `forbidden_tags ∩ current_tags = ∅`

Same logic applies to step windows: restrict by FSM, domain, danger level.

---

## 3. Practical recommendation

| Store | Stores | Used for |
|-------|--------|----------|
| **Neo4j** | Steps, edges, artifacts, pattern instances | Traversal, constraints, provenance audit |
| **Qdrant** | Vectors for steps, windows, patterns | Recall (top-K candidates) |

**Glue:** Store the Qdrant point ID in Neo4j node properties (`step.qdrant_id`, `pattern.qdrant_id`). Store `trace/domain/tag/danger` fields in Qdrant payload for filtering.
