# Canonical Schemas

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
    # keep small; extend with your own taxonomy
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
    # optional: include your known tool names
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
    source_id: Optional[str] = None  # e.g., HF dataset name, repo slug
    uri: Optional[HttpUrl] = None
    split: Optional[str] = None  # train/test/validation
    record_id: Optional[str] = None  # original record key
    created_at: Optional[datetime] = None


class Provenance(BaseModel):
    sources: List[SourceRef] = Field(default_factory=list)
    license_info: LicenseInfo = Field(default_factory=LicenseInfo)
    sensitivity: Sensitivity = Sensitivity.PUBLIC

    # pipeline lineage
    ingested_at: Optional[datetime] = None
    pipeline_version: Optional[str] = None
    schema_version: str = "v1"
    notes: Optional[str] = None


# -----------------------------
# FSM + roles
# -----------------------------

class FSMId(str, Enum):
    # ~10 universal FSMs
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
    # shared state vocabulary
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
    model: str  # e.g., "text-embedding-3-large" or local model name
    dim: int
    # where it lives (vector DB key, file path, etc.)
    storage_key: str
    created_at: Optional[datetime] = None

    # optional: normalized content hash to avoid duplicates
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

    # common structured fields (optional, depending on type)
    tags: List[str] = Field(default_factory=list)
    domain: Optional[DomainTag] = None

    # “authority level” / priority for constraints, etc.
    priority: Optional[int] = Field(default=None, ge=0, le=10)

    # generic structured payload (keep small; don’t dump huge blobs)
    data: Dict[str, Any] = Field(default_factory=dict)

    # embeddings (optional)
    embedding: Optional[EmbeddingRef] = None


# -----------------------------
# Steps
# -----------------------------

class ToolCall(BaseModel):
    tool: ToolName = ToolName.NONE
    name: Optional[str] = None  # e.g., specific function name
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = Field(default=None, ge=0)


class Step(BaseModel):
    step_id: IdStr
    trace_id: IdStr

    index: int = Field(ge=0)
    created_at: Optional[datetime] = None

    # speaker / origin
    actor: Literal["user", "assistant", "tool", "system"] = "assistant"

    role: StepRole = StepRole.OTHER
    text: str

    # FSM annotations (can be filled by your labeler)
    fsm_id: Optional[FSMId] = None
    fsm_state: Optional[FSMState] = None

    # danger routing snapshot at the time of this step (optional)
    danger: Optional[DangerScores] = None

    # tool details if relevant
    tool_call: Optional[ToolCall] = None

    # references to artifacts mentioned/created/used
    artifact_refs: List[IdStr] = Field(default_factory=list)

    # embeddings for retrieval
    embedding: Optional[EmbeddingRef] = None

    # lightweight quality/properties for mining
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
    INSTANCE_OF = "instance_of"  # step/trace belongs to a Pattern
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
    trace_id: Optional[IdStr] = None  # helpful if you scope edges per trace

    type: EdgeType
    src: NodeRef
    dst: NodeRef

    # optional qualifiers
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

    # optional: initial problem statement (normalized)
    problem: Optional[str] = None

    # danger snapshot at start
    initial_danger: Optional[DangerScores] = None

    # success / outcome proxy (optional, but useful for mining)
    outcome: Dict[str, Any] = Field(default_factory=dict)

    # counts
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
    # a normalized template step: role/state + text with slots
    role: StepRole
    fsm_state: Optional[FSMState] = None
    text_template: str  # e.g., "Define metric: {metric} with target {target}"

    # slot definitions
    slots: Dict[str, str] = Field(default_factory=dict)  # slot_name -> description


class PatternApplicability(BaseModel):
    # when to use this pattern
    fsm_id: Optional[FSMId] = None
    allowed_states: List[FSMState] = Field(default_factory=list)

    domains: List[DomainTag] = Field(default_factory=list)
    required_tags: List[str] = Field(default_factory=list)
    forbidden_tags: List[str] = Field(default_factory=list)

    # danger conditions (e.g. requires ambiguity low)
    min_danger: Dict[DangerType, float] = Field(default_factory=dict)
    max_danger: Dict[DangerType, float] = Field(default_factory=dict)


class PatternQuality(BaseModel):
    # quality signals and aggregates; populate from mining
    support: int = Field(default=0, ge=0)  # number of instances
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

    # canonical embedding for semantic retrieval
    embedding: Optional[EmbeddingRef] = None

    # quality stats
    quality: PatternQuality = Field(default_factory=PatternQuality)

    # provenance/versioning
    created_at: Optional[datetime] = None
    miner_version: Optional[str] = None
    schema_version: str = "v1"


class PatternInstance(BaseModel):
    instance_id: IdStr
    pattern_id: IdStr
    trace_id: IdStr

    # which steps instantiate the pattern
    step_ids: List[IdStr] = Field(default_factory=list)

    # extracted slot values (if any)
    bindings: Dict[str, Any] = Field(default_factory=dict)

    # outcome info for this instance
    success_proxy: Optional[float] = Field(default=None, ge=0.0, le=1.0)


# -----------------------------
# Bundle object (useful for IO)
# -----------------------------

class TraceBundle(BaseModel):
    trace: Trace
    steps: List[Step] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)

    # optional: mined patterns attached
    patterns: List[Pattern] = Field(default_factory=list)
    pattern_instances: List[PatternInstance] = Field(default_factory=list)

    @model_validator(mode="after")
    def _basic_consistency(self) -> "TraceBundle":
        # ensure step.trace_id matches
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

Notes on how to use this schema (quick)

Ingestion: convert any dataset record into a TraceBundle(trace, steps, artifacts, edges) even if you initially only fill steps + NEXT edges.

Labeling: later enrich Step.fsm_id, Step.fsm_state, Step.role, Step.danger.

Mining: create Pattern + PatternInstance, and add INSTANCE_OF edges if you want the graph to expose it directly.