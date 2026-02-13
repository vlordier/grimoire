"""
Canonical, storage-agnostic Pydantic v2 schema for Grimoire.

Derived from docs/reference/canonical-schemas.md.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

IdStr = str


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
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


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
        description=(
            "Top regex hits + probe answers for debuggability. "
            "See DangerEvidence in danger_router_pydantic.py for the full typed model."
        ),
    )

    @model_validator(mode="after")
    def _ensure_keys(self) -> "DangerScores":
        for danger_type in DangerType:
            value = float(self.scores.get(danger_type, 0.0))
            self.scores[danger_type] = clip01(value)
        return self

    def score(self, danger_type: DangerType) -> float:
        return float(self.scores.get(danger_type, 0.0))


class EmbeddingRef(BaseModel):
    embedding_id: IdStr
    model: str
    dim: int
    storage_key: str
    created_at: Optional[datetime] = None
    content_hash: Optional[str] = None


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
    def _non_empty_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("step.text must be non-empty")
        return trimmed


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


class TraceBundle(BaseModel):
    trace: Trace
    steps: List[Step] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    patterns: List[Pattern] = Field(default_factory=list)
    pattern_instances: List[PatternInstance] = Field(default_factory=list)

    @model_validator(mode="after")
    def _basic_consistency(self) -> "TraceBundle":
        for step in self.steps:
            if step.trace_id != self.trace.trace_id:
                raise ValueError(f"step {step.step_id} trace_id mismatch")
        return self


def make_node_ref_step(step_id: str) -> NodeRef:
    return NodeRef(type=NodeRefType.STEP, id=step_id)


def make_node_ref_artifact(artifact_id: str) -> NodeRef:
    return NodeRef(type=NodeRefType.ARTIFACT, id=artifact_id)


__all__ = [
    "IdStr",
    "SourceType",
    "LicenseType",
    "Sensitivity",
    "DomainTag",
    "ToolName",
    "LicenseInfo",
    "SourceRef",
    "Provenance",
    "FSMId",
    "FSMState",
    "StepRole",
    "DangerType",
    "DangerScores",
    "EmbeddingRef",
    "ArtifactType",
    "Artifact",
    "ToolCall",
    "Step",
    "EdgeType",
    "NodeRefType",
    "NodeRef",
    "Edge",
    "Trace",
    "PatternType",
    "PatternTemplateStep",
    "PatternApplicability",
    "PatternQuality",
    "Pattern",
    "PatternInstance",
    "TraceBundle",
    "make_node_ref_step",
    "make_node_ref_artifact",
]
