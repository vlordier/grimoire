"""
neo4j_and_qdrant_mapping.md (as code block for copy/paste)

Goal: 1:1 mapping between canonical_schema.py and:
- Neo4j property graph (labels + relationship types + key properties)
- Qdrant payloads (points + metadata + filtering strategy)

Assumptions:
- Use ULIDs/UUIDs as string ids.
- Use Neo4j constraints on id uniqueness.
- Store vectors in Qdrant, store structure in Neo4j.
- Keep “text blobs” small in Neo4j; large blobs go to object storage with a key.

This file is intentionally concrete and implementable.
"""

# =============================
# 1) NEO4J MAPPING
# =============================

"""
Node labels (one primary label + optional secondary labels):
- :Trace
- :Step
- :Artifact
- :Pattern
- :Embedding (optional, if you want explicit nodes; otherwise keep embedding as properties)
- :Source (optional, for provenance)
- :License (optional)

Recommended: keep it simple: Trace/Step/Artifact/Pattern nodes only, store provenance as properties.
"""

# -----
# 1.1 Constraints / indexes (Cypher)
# -----

"""
// Uniqueness
CREATE CONSTRAINT trace_id_unique IF NOT EXISTS
FOR (n:Trace) REQUIRE n.trace_id IS UNIQUE;

CREATE CONSTRAINT step_id_unique IF NOT EXISTS
FOR (n:Step) REQUIRE n.step_id IS UNIQUE;

CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (n:Artifact) REQUIRE n.artifact_id IS UNIQUE;

CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (n:Pattern) REQUIRE n.pattern_id IS UNIQUE;

// Helpful indexes
CREATE INDEX trace_domain IF NOT EXISTS FOR (n:Trace) ON (n.domain);
CREATE INDEX step_trace_index IF NOT EXISTS FOR (n:Step) ON (n.trace_id, n.index);
CREATE INDEX step_role IF NOT EXISTS FOR (n:Step) ON (n.role);
CREATE INDEX step_fsm IF NOT EXISTS FOR (n:Step) ON (n.fsm_id, n.fsm_state);
CREATE INDEX artifact_type IF NOT EXISTS FOR (n:Artifact) ON (n.type);
CREATE INDEX pattern_type IF NOT EXISTS FOR (n:Pattern) ON (n.type);
"""

# -----
# 1.2 Node property mapping (canonical -> neo4j)
# -----

"""
:Trace
- trace_id (string, PK)
- title (string)
- domain (string)
- tags (list[string])
- problem (string) [optional; can store truncated]
- created_at, updated_at (datetime or string)
- provenance_* flattened:
  - provenance_source_types (list[string])  // from SourceRef.source_type
  - provenance_source_ids (list[string])    // from SourceRef.source_id
  - provenance_uris (list[string])
  - license (string)
  - license_url (string)
  - attribution (string)
  - sensitivity (string)
  - ingested_at (string)
  - pipeline_version (string)
  - schema_version (string)
- initial_danger_* flattened (optional):
  - danger_ambiguity (float)
  - danger_adversarial (float)
  - danger_irreversibility (float)
  - danger_institutional (float)
- outcome (map serialized to JSON string OR store selected scalar fields)
- n_steps (int)

:Step
- step_id (string, PK)
- trace_id (string, FK for convenience)
- index (int)
- created_at (string)
- actor (string)
- role (string)
- text (string) [store raw or truncated; full text can be stored if acceptable]
- fsm_id (string)
- fsm_state (string)
- danger_* snapshot (optional floats)
- tool_* flattened (optional):
  - tool (string)
  - tool_name (string)
  - tool_args_json (string)
  - tool_result_json (string)
  - tool_error (string)
  - latency_ms (int)
- embedding_ref fields if you want:
  - embedding_id (string)
  - embedding_model (string)
  - embedding_dim (int)
  - embedding_storage_key (string)
  - embedding_hash (string)
- properties_json (string) or store selected fields

:Artifact
- artifact_id (string, PK)
- type (string)
- title (string)
- text (string) [optional]
- tags (list[string])
- domain (string)
- priority (int)
- data_json (string)
- embedding_* (same as above optional)

:Pattern
- pattern_id (string, PK)
- type (string)
- name (string)
- description (string)
- applicability_json (string) OR flatten key fields:
  - fsm_id
  - allowed_states (list[string])
  - domains (list[string])
  - required_tags (list[string])
  - forbidden_tags (list[string])
  - min_danger_* (floats)
  - max_danger_* (floats)
- template_json (string)   // list[PatternTemplateStep]
- embedding_* (same)
- quality_*:
  - support (int)
  - avg_revision_loops (float)
  - verification_rate (float)
  - success_proxy (float)
- created_at (string)
- miner_version (string)
- schema_version (string)
"""

# -----
# 1.3 Relationship types (EdgeType -> Neo4j relationship)
# -----

"""
Core structural relationships (between :Step nodes):
- (:Step)-[:NEXT]->(:Step)                 // EdgeType.NEXT (sequence)
- (:Step)-[:SUPPORTS]->(:Step)             // EdgeType.SUPPORTS
- (:Step)-[:REFUTES]->(:Step)              // EdgeType.REFUTES
- (:Step)-[:REVISES]->(:Step)              // EdgeType.REVISES
- (:Step)-[:DEPENDS_ON]->(:Step|:Artifact) // EdgeType.DEPENDS_ON

Linking steps to artifacts:
- (:Step)-[:MENTIONS]->(:Artifact)         // EdgeType.MENTIONS
- (:Step)-[:EVIDENCE_FOR]->(:Artifact)     // EdgeType.EVIDENCE_FOR
- (:Step)-[:DECISION_FOR]->(:Artifact)     // EdgeType.DECISION_FOR
- (:Step)-[:CREATES]->(:Artifact)          // (not in EdgeType; useful extension)
- (:Step)-[:USES]->(:Artifact)             // (optional)

Trace containment:
- (:Trace)-[:HAS_STEP]->(:Step)
- (:Trace)-[:HAS_ARTIFACT]->(:Artifact)
- (:Trace)-[:HAS_PATTERN_INSTANCE]->(:PatternInstance) (optional modeling)

Patterns:
- (:Pattern)-[:HAS_TEMPLATE_STEP]->(:TemplateStep)      // optional; usually keep JSON
- (:Step)-[:INSTANCE_OF {instance_id, bindings_json, success_proxy}]->(:Pattern)
  // EdgeType.INSTANCE_OF with properties
"""

# -----
# 1.4 Edge properties mapping
# -----

"""
All relationships can have:
- edge_id (string)
- weight (float)
- label (string)
- data_json (string)

Example:
(:Step {step_id})-[:NEXT {edge_id, weight}]->(:Step {step_id})
"""

# -----
# 1.5 Minimal ingestion Cypher patterns
# -----

"""
// Create a Trace
MERGE (t:Trace {trace_id: $trace_id})
SET t += $trace_props;

// Create Steps
UNWIND $steps AS s
MERGE (st:Step {step_id: s.step_id})
SET st += s.props
MERGE (t:Trace {trace_id: s.trace_id})
MERGE (t)-[:HAS_STEP]->(st);

// Sequence edges
UNWIND $next_edges AS e
MATCH (a:Step {step_id: e.src}), (b:Step {step_id: e.dst})
MERGE (a)-[r:NEXT]->(b)
SET r += e.props;

// Artifacts
UNWIND $artifacts AS a
MERGE (ar:Artifact {artifact_id: a.artifact_id})
SET ar += a.props
MERGE (t:Trace {trace_id: a.trace_id})
MERGE (t)-[:HAS_ARTIFACT]->(ar);

// Mentions
UNWIND $mentions AS m
MATCH (st:Step {step_id: m.step_id}), (ar:Artifact {artifact_id: m.artifact_id})
MERGE (st)-[r:MENTIONS]->(ar)
SET r += m.props;
"""

# =============================
# 2) QDRANT PAYLOAD MAPPING
# =============================

"""
Principle: Qdrant stores vectors and filterable metadata; Neo4j stores structure.

You will store multiple "collections" for different retrieval granularities:
1) steps          - vector per Step
2) step_windows   - vector per window of k steps (procedural chunk)
3) patterns       - vector per Pattern prototype

Optionally 4) traces - vector per whole trace
"""

# -----
# 2.1 Qdrant collection schemas
# -----

"""
Collection: steps
Point ID: step_id (string) OR hashed int; easiest: string id
Vector: embedding vector for Step.text
Payload fields (1:1 with Step + Trace minimal routing):
- step_id: str
- trace_id: str
- index: int
- actor: str
- role: str
- fsm_id: str | null
- fsm_state: str | null
- domain: str (from Trace.domain)
- tags: list[str] (Trace.tags + Step.properties["tags"] if you add)
- danger_ambiguity/adversarial/irreversibility/institutional: float | null
- has_tool_call: bool
- tool: str | null
- created_at: str | null
- provenance:
  - source_type: list[str]
  - source_id: list[str]
  - license: str
  - sensitivity: str

Keep Step.text out of payload if you want smaller payloads; store it in a doc store keyed by step_id.

Filtering examples:
- role == "plan"
- fsm_id == "fsm_diagnose_fix" AND fsm_state == "S3_plan"
- domain in ["ml","software"]
- danger_irreversibility < 0.3
"""

"""
Collection: step_windows
Point ID: window_id (string; e.g., "{trace_id}:{start}:{k}")
Vector: embedding of concatenated steps text (or compressed summary)
Payload:
- window_id: str
- trace_id: str
- start_index: int
- k: int
- step_ids: list[str]
- fsm_id: str | null (dominant among steps)
- fsm_state: str | null (state at end of window is useful)
- domain: str
- tags: list[str]
- danger_* (max or avg over window)
- has_tool_call: bool
- license/sensitivity/source like above

This is your best "procedural similarity" index.
"""

"""
Collection: patterns
Point ID: pattern_id (string)
Vector: pattern.embedding (prototype)
Payload:
- pattern_id: str
- type: str
- name: str
- description: str (optional)
- fsm_id: str | null
- allowed_states: list[str]
- domains: list[str]
- required_tags: list[str]
- forbidden_tags: list[str]
- min_danger_*: float | null
- max_danger_*: float | null
- quality_support: int
- quality_success_proxy: float | null
- miner_version: str | null
- schema_version: str
"""

# -----
# 2.2 1:1 mapping helpers (what goes where)
# -----

"""
EmbeddingRef mapping:
- embedding_id: stored in Neo4j as property if you want
- vector itself is stored in Qdrant
- storage_key: in Qdrant you don’t need it; in Neo4j it can store the qdrant point reference

Recommended:
- In Neo4j, store:
  - step.embedding_id = step_id (or separate)
  - step.embedding_model
  - step.embedding_dim
  - step.embedding_point = step_id
- In Qdrant, you store the vector and payload; no need to mirror storage_key unless you use multi-store.
"""

# -----
# 2.3 Qdrant payload fields: explicit dict shapes
# -----

STEP_PAYLOAD_EXAMPLE = {
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
    "has_tool_call": False,
    "tool": None,
    "created_at": "2026-02-12T10:00:00Z",
    "source_type": ["huggingface"],
    "source_id": ["open-thoughts/OpenThoughts-114k"],
    "license": "cc-by",
    "sensitivity": "public",
}

WINDOW_PAYLOAD_EXAMPLE = {
    "window_id": "01J...TRACE:10:5",
    "trace_id": "01J...TRACE",
    "start_index": 10,
    "k": 5,
    "step_ids": ["...","..."],
    "fsm_id": "fsm_diagnose_fix",
    "fsm_state": "S6_evaluate",
    "domain": "software",
    "tags": ["debugging"],
    "danger_ambiguity": 0.20,  # max or avg
    "danger_adversarial": 0.00,
    "danger_irreversibility": 0.10,
    "danger_institutional": 0.05,
    "has_tool_call": True,
    "license": "mit",
    "sensitivity": "public",
}

PATTERN_PAYLOAD_EXAMPLE = {
    "pattern_id": "01J...PATTERN",
    "type": "fsm_subpath",
    "name": "Hypothesis → discriminating test → update belief",
    "fsm_id": "fsm_diagnose_fix",
    "allowed_states": ["S2_model","S3_plan","S4_execute","S5_observe","S6_evaluate"],
    "domains": ["software","ml"],
    "required_tags": ["debug"],
    "forbidden_tags": [],
    "min_danger_ambiguity": None,
    "max_danger_irreversibility": 0.8,  # example
    "quality_support": 1420,
    "quality_success_proxy": 0.71,
    "miner_version": "miner_v3",
    "schema_version": "v1",
}

# -----
# 2.4 Filtering strategy (must-have for correctness)
# -----

"""
When retrieving next-step patterns, you should filter by:
- FSM compatibility:
  patterns.fsm_id == current_fsm_id (or allow generic patterns)
  AND current_state in patterns.allowed_states

- Danger constraints:
  if irreversibility dominant, prefer patterns whose max_danger_irreversibility >= current score
  or patterns that explicitly include verification gates

- Domain/tags:
  domain in patterns.domains (if set)
  required_tags subset of current tags
  forbidden_tags disjoint

Same for step windows:
- restrict to same FSM or same domain when possible
- exclude windows with higher danger than current if you are in a “low risk” mode (optional)
"""

# =============================
# 3) PRACTICAL RECOMMENDATION
# =============================

"""
Neo4j:
- store all steps + edges + artifacts + pattern instances
- use it for traversal + constraints + provenance audit

Qdrant:
- store vectors for steps, windows, patterns
- use it for recall (top-K candidates)

Glue:
- store the Qdrant point ID in Neo4j node properties (step.qdrant_id, pattern.qdrant_id)
- store trace/domain/tag/danger fields in Qdrant payload for filtering
"""

