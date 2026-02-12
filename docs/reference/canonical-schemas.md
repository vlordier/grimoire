# Canonical Schemas

> **Authoritative Pydantic v2 contract** for the entire system. All ingestion, storage, mining, and retrieval layers import from or align to these models.
>
> **See also:** [Storage Mapping](storage-mapping.md) (Neo4j + Qdrant implementation) · [Qdrant Setup](qdrant-setup.md) · [Pattern Detection & Pipeline](pattern-detection-and-pipeline.md) · [FSM Catalogue](../domain/fsm-catalogue.md) · [Danger Classification](../domain/danger-classification.md) · [Feature Spec: Canonical Schema Implementation](../../specs/001-canonical-schema-implementation/)

---

```python
"""
canonical_schema.py (Pydantic v2)

Canonical, storage-agnostic schema for:
- Traces (datasets / conversations / runs)
- Steps (events)
- Artifacts (goal/constraint/assumption/etc.)
- Edges (graph structure)
- Patterns (meta-thoughts) + Instances
- Embeddings + Provenance + Licensing

This is intended as your single contract across:
- ingestion (HF datasets, logs)
- graph DB (Neo4j/AGE/Memgraph)
- vector DB (Qdrant/Weaviate/pgvector)
- evaluation + mining

Requires: pydantic>=2
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


# -----------------------------
# Basic primitives
# -----------------------------

IdStr = str  # use ULID/UUID in practice


class SourceType(str, Enum):
    HUGGINGFACE = "huggingface"
    CHAT = "chat"
    TOOL_RUN = "tool_run"
    REPO = "repo"
    PAPER = "paper"
    OTHER = "other"


class LicenseType(str, Enum):
    UNKNOWN = "unknown"
    CC_BY = "cc-by"
    CC_BY_SA = "cc-by-sa"
    CC_BY_NC = "cc-by-nc"
    CC0 = "cc0"
    APACHE_2 = "apache-2.0"
    MIT = "mit"
    GPL = "gpl"
    PROPRIETARY = "proprietary"
    CUSTOM = "custom"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"


class DomainTag(str, Enum):
    GENERAL = "general"
    SOFTWARE = "software"
    ML = "ml"
    DATA = "data"
    SECURITY = "security"
    PRODUCT = "product"
    LEGAL = "legal"
    HEALTH = "health"
    FINANCE = "finance"


class ToolName(str, Enum):
    NONE = "none"
    PYTHON = "python"
    SQL = "sql"
    BROWSER = "browser"
    SHELL = "shell"
    OTHER = "other"


def clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


# -----------------------------
# Provenance / licensing
# -----------------------------

class LicenseInfo(BaseModel):
    license: LicenseType = LicenseType.UNKNOWN
    license_url: Optional[HttpUrl] = None
    attribution: Optional[str] = None
    notes: Optional[str] = None


class SourceRef(BaseModel):
    source_type: SourceType
    source_id: Optional[str] = None
    uri: Optional[HttpUrl] = None
    split: Optional[str] = None
    record_id: Optional[str] = None
    created_at: Optional[datetime] = None


class Provenance(BaseModel):
    sources: List[SourceRef] = Field(default_factory=list)
    license_info: LicenseInfo = Field(default_factory=LicenseInfo)
    sensitivity: Sensitivity = Sensitivity.PUBLIC

    ingested_at: Optional[datetime] = None
    pipeline_version: Optional[str] = None
    schema_version: str = "v1"
    notes: Optional[str] = None


# -----------------------------
# FSM + roles
# -----------------------------

class FSMId(str, Enum):
    CLARIFY_FRAME = "fsm_clarify_frame"
    DIAGNOSE_FIX = "fsm_diagnose_fix"
    DESIGN_DECIDE = "fsm_design_decide"
    OPTIMIZE = "fsm_optimize"
    VERIFY = "fsm_verify"
    TRANSFORM = "fsm_transform"
    OPERATE_HARDEN = "fsm_operate_harden"
    POSTMORTEM = "fsm_postmortem"
    RESOLVE_CONFLICT = "fsm_resolve_conflict"
    ADVERSARIAL_LOOP = "fsm_adversarial_loop"


class FSMState(str, Enum):
    S0_INTAKE = "S0_intake"
    S1_CLARIFY = "S1_clarify"
    S2_MODEL = "S2_model"
    S3_PLAN = "S3_plan"
    S4_EXECUTE = "S4_execute"
    S5_OBSERVE = "S5_observe"
    S6_EVALUATE = "S6_evaluate"
    S7_DECIDE = "S7_decide"
    S8_HARDEN = "S8_harden"
    S9_CLOSE = "S9_close"


class StepRole(str, Enum):
    GOAL = "goal"
    QUESTION = "question"
    PLAN = "plan"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    CRITIQUE = "critique"
    REVISION = "revision"
    DECISION = "decision"
    VERIFICATION = "verification"
    SUMMARY = "summary"
    OTHER = "other"


class DangerType(str, Enum):
    AMBIGUITY = "ambiguity"
    ADVERSARIAL = "adversarial"
    IRREVERSIBILITY = "irreversibility"
    INSTITUTIONAL = "institutional"


class DangerScores(BaseModel):
    scores: Dict[DangerType, float] = Field(default_factory=dict)
    evidence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Top regex hits + probe answers for debuggability. "
        "See DangerEvidence in danger_router_pydantic.py for the full typed model.",
    )

    @model_validator(mode="after")
    def _ensure_keys(self) -> "DangerScores":
        for dt in DangerType:
            self.scores[dt] = clip01(float(self.scores.get(dt, 0.0)))
        return self

    def score(self, dt: DangerType) -> float:
        return float(self.scores.get(dt, 0.0))


# -----------------------------
# Embeddings
# -----------------------------

class EmbeddingRef(BaseModel):
    embedding_id: IdStr
    model: str
    dim: int
    storage_key: str
    created_at: Optional[datetime] = None
    content_hash: Optional[str] = None


# -----------------------------
# Artifacts (first-class nodes)
# -----------------------------

class ArtifactType(str, Enum):
    GOAL = "goal"
    SCOPE = "scope"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    OPTION = "option"
    RISK = "risk"
    METRIC = "metric"
    TEST = "test"
    EVIDENCE = "evidence"
    DECISION = "decision"
    MONITOR = "monitor"
    STAKEHOLDER = "stakeholder"
    VETO_POINT = "veto_point"
    THREAT = "threat"
    DEFENSE = "defense"
    RUNBOOK = "runbook"
    OTHER = "other"


class Artifact(BaseModel):
    artifact_id: IdStr
    type: ArtifactType

    title: Optional[str] = None
    text: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    domain: Optional[DomainTag] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    data: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[EmbeddingRef] = None


# -----------------------------
# Steps
# -----------------------------

class ToolCall(BaseModel):
    tool: ToolName = ToolName.NONE
    name: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = Field(default=None, ge=0)


class Step(BaseModel):
    step_id: IdStr
    trace_id: IdStr

    index: int = Field(ge=0)
    created_at: Optional[datetime] = None

    actor: Literal["user", "assistant", "tool", "system"] = "assistant"
    role: StepRole = StepRole.OTHER
    text: str

    fsm_id: Optional[FSMId] = None
    fsm_state: Optional[FSMState] = None
    danger: Optional[DangerScores] = None

    tool_call: Optional[ToolCall] = None
    artifact_refs: List[IdStr] = Field(default_factory=list)
    embedding: Optional[EmbeddingRef] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, v: str) -> str:
        vv = v.strip()
        if not vv:
            raise ValueError("step.text must be non-empty")
        return vv


# -----------------------------
# Edges (graph structure)
# -----------------------------

class EdgeType(str, Enum):
    NEXT = "next"
    SUPPORTS = "supports"
    REFUTES = "refutes"
    REVISES = "revises"
    DEPENDS_ON = "depends_on"
    USES_TOOL = "uses_tool"
    MENTIONS = "mentions"
    EVIDENCE_FOR = "evidence_for"
    DECISION_FOR = "decision_for"
    INSTANCE_OF = "instance_of"
    CREATES = "creates"
    USES = "uses"
    OTHER = "other"


class NodeRefType(str, Enum):
    TRACE = "trace"
    STEP = "step"
    ARTIFACT = "artifact"
    PATTERN = "pattern"


class NodeRef(BaseModel):
    type: NodeRefType
    id: IdStr


class Edge(BaseModel):
    edge_id: IdStr
    trace_id: Optional[IdStr] = None

    type: EdgeType
    src: NodeRef
    dst: NodeRef

    weight: Optional[float] = Field(default=None, ge=0.0)
    label: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------
# Trace (top-level)
# -----------------------------

class Trace(BaseModel):
    trace_id: IdStr
    title: Optional[str] = None

    domain: DomainTag = DomainTag.GENERAL
    tags: List[str] = Field(default_factory=list)

    provenance: Provenance = Field(default_factory=Provenance)
    problem: Optional[str] = None
    initial_danger: Optional[DangerScores] = None
    outcome: Dict[str, Any] = Field(default_factory=dict)
    n_steps: Optional[int] = Field(default=None, ge=0)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# -----------------------------
# Patterns (meta-thoughts)
# -----------------------------

class PatternType(str, Enum):
    FSM_SUBPATH = "fsm_subpath"
    GRAPH_MOTIF = "graph_motif"
    SEMANTIC_CLUSTER = "semantic_cluster"
    MANUAL = "manual"


class PatternTemplateStep(BaseModel):
    role: StepRole
    fsm_state: Optional[FSMState] = None
    text_template: str
    slots: Dict[str, str] = Field(default_factory=dict)


class PatternApplicability(BaseModel):
    fsm_id: Optional[FSMId] = None
    allowed_states: List[FSMState] = Field(default_factory=list)
    domains: List[DomainTag] = Field(default_factory=list)
    required_tags: List[str] = Field(default_factory=list)
    forbidden_tags: List[str] = Field(default_factory=list)
    min_danger: Dict[DangerType, float] = Field(default_factory=dict)
    max_danger: Dict[DangerType, float] = Field(default_factory=dict)


class PatternQuality(BaseModel):
    support: int = Field(default=0, ge=0)
    avg_revision_loops: Optional[float] = Field(default=None, ge=0.0)
    verification_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    success_proxy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    last_updated_at: Optional[datetime] = None


class Pattern(BaseModel):
    pattern_id: IdStr
    type: PatternType

    name: str
    description: Optional[str] = None

    applicability: PatternApplicability = Field(default_factory=PatternApplicability)
    template: List[PatternTemplateStep] = Field(default_factory=list)
    embedding: Optional[EmbeddingRef] = None
    quality: PatternQuality = Field(default_factory=PatternQuality)

    created_at: Optional[datetime] = None
    miner_version: Optional[str] = None
    schema_version: str = "v1"


class PatternInstance(BaseModel):
    instance_id: IdStr
    pattern_id: IdStr
    trace_id: IdStr

    step_ids: List[IdStr] = Field(default_factory=list)
    bindings: Dict[str, Any] = Field(default_factory=dict)
    success_proxy: Optional[float] = Field(default=None, ge=0.0, le=1.0)


# -----------------------------
# Bundle object (useful for IO)
# -----------------------------

class TraceBundle(BaseModel):
    trace: Trace
    steps: List[Step] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)

    patterns: List[Pattern] = Field(default_factory=list)
    pattern_instances: List[PatternInstance] = Field(default_factory=list)

    @model_validator(mode="after")
    def _basic_consistency(self) -> "TraceBundle":
        for s in self.steps:
            if s.trace_id != self.trace.trace_id:
                raise ValueError(f"step {s.step_id} trace_id mismatch")
        return self


# -----------------------------
# Minimal example constructors
# -----------------------------

def make_node_ref_step(step_id: str) -> NodeRef:
    return NodeRef(type=NodeRefType.STEP, id=step_id)


def make_node_ref_artifact(artifact_id: str) -> NodeRef:
    return NodeRef(type=NodeRefType.ARTIFACT, id=artifact_id)
```

---

## Usage notes

1. **Ingestion:** Convert any dataset record into a `TraceBundle(trace, steps, artifacts, edges)` — even if you initially only fill steps + `NEXT` edges.
2. **Labeling:** Later enrich `Step.fsm_id`, `Step.fsm_state`, `Step.role`, `Step.danger`.
3. **Mining:** Create `Pattern` + `PatternInstance`, and add `INSTANCE_OF` edges if you want the graph to expose it directly.

---

## See also

- [Feature Spec: Canonical Schema Implementation - Data Model](/specs/001-canonical-schema-implementation/data-model.md) — Pydantic v2 implementations with validators and examples
- [Storage Mapping Reference](storage-mapping.md) — How canonical schemas map to Neo4j properties and Qdrant payloads
- [Ingestion API Contract](/specs/001-canonical-schema-implementation/contracts/ingestion-api.md) — HuggingFace dataset normalization pipeline
- [Storage API Contract](/specs/001-canonical-schema-implementation/contracts/storage-api.md) — Neo4j persistence with atomic transactions
- [Retrieval API Contract](/specs/001-canonical-schema-implementation/contracts/retrieval-api.md) — Qdrant vector search with metadata filtering
