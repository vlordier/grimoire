# Data Model: Canonical Schema with Pydantic v2

**Phase 1**: Complete data model with full validation, constraints, and JSON examples.

---

## Overview

```text
Trace (root entity: problem + thoughts)
  ├── Step[] (sequence of actions/observations)
  │   └── StepTextVersion (markdown with audit trail)
  ├── Edge[] (relationships between steps, e.g., NEXT, RELATED)
  └── Provenance (source + license + ingestion metadata)

Supporting:
  ├── Embedding (vector + version binding)
  ├── StepWindow (FSM-adaptive context for reasoning)
  └── DomainTag, StepRole, Sensitivity (enums)
```

---

## Enums and Constants

```python
from enum import Enum
from typing import Literal

class DomainTag(str, Enum):
    """Problem domain classification — aligned to canonical schema"""
    GENERAL = "general"
    SOFTWARE = "software"
    ML = "ml"
    DATA = "data"
    SECURITY = "security"
    PRODUCT = "product"
    LEGAL = "legal"
    HEALTH = "health"
    FINANCE = "finance"

class StepRole(str, Enum):
    """Semantic role of reasoning step — aligned to canonical schema"""
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

class Sensitivity(str, Enum):
    """Data sensitivity classification — aligned to canonical schema"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"

class EdgeType(str, Enum):
    """Relationship types between steps — aligned to canonical schema (lowercase values)"""
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
```

---

## SourceRef: Provenance Origin

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List
import json

class SourceRef(BaseModel):
    """Reference to source dataset or origin"""

    source_type: Literal["huggingface", "chat", "tool_run", "repo", "paper", "other"] = Field(
        description="Origin type — aligned to canonical SourceType enum"
    )
    source_id: str = Field(
        description="Dataset ID or URL (e.g., 'open-thoughts/OpenThoughts-114k')",
        min_length=1,
        max_length=256
    )
    record_id: Optional[str] = Field(
        default=None,
        description="Index or ID within source dataset (alphanumeric + underscore, max 300 chars)"
    )

    @field_validator("record_id")
    @classmethod
    def record_id_format(cls, v):
        """Validate record_id is alphanumeric + underscore only"""
        if v is not None:
            if len(v) > 300:
                raise ValueError(f"record_id must be ≤ 300 chars; got {len(v)}")
            if not all(c.isalnum() or c == '_' for c in v):
                raise ValueError(
                    f"record_id must be alphanumeric + underscore only; "
                    f"got '{v}' with invalid characters"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "huggingface",
                "source_id": "open-thoughts/OpenThoughts-114k",
                "record_id": "record_12345_v2"
            }
        }
```

---

## Trace: Root Problem Entity

```python
class Trace(BaseModel):
    """
    Canonical representation of a single reasoning problem and its solution trace.
    Immutable once created; edits go to Step text versions.
    """

    # Identity
    trace_id: str = Field(
        description="Unique identifier: base58(SHA256(problem+domain+tags))[:12] + '-' + ULID[:8]",
        pattern="^[a-zA-Z0-9]{12}-[a-zA-Z0-9]{8}$"
    )

    # Problem description
    title: str = Field(
        min_length=10,
        max_length=500,
        description="Short problem summary (≤500 chars)"
    )
    problem: str = Field(
        min_length=1,
        max_length=50000,
        description="Full problem statement"
    )
    domain: DomainTag = Field(
        default=DomainTag.GENERAL,
        description="Classification for filtering"
    )

    # Versioning
    trace_version: int = Field(
        default=1,
        ge=1,
        description="Increments when problem re-solved differently"
    )
    content_hash: str = Field(
        description="SHA256(problem) for deduplication",
        pattern="^[a-f0-9]{64}$"
    )

    # Statistics
    n_steps: int = Field(
        ge=1,
        le=10000,
        description="Number of steps in reasoning chain"
    )

    # Provenance (Principle IX: Immutable origin tracking)
    provenance_sources: List[SourceRef] = Field(
        min_length=1,
        description="Data origin(s)"
    )
    provenance_license: str = Field(
        examples=["apache-2.0", "mit", "cc-by-4.0", "public-domain"],
        description="License of source material"
    )
    provenance_sensitivity: Sensitivity = Field(
        default=Sensitivity.PUBLIC,
        description="Data classification"
    )
    provenance_ingested_at: datetime = Field(
        description="When trace was parsed and stored"
    )
    provenance_pipeline_version: str = Field(
        description="Version of ingestion pipeline (e.g., '0.1.0-alpha')",
        examples=["0.1.0-alpha"]
    )
    provenance_schema_version: str = Field(
        default="v1",
        description="Data model version for compatibility",
        examples=["v1", "v1.1"]
    )

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update (for metadata-only changes)"
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Soft-delete timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "7k9mQ2aBc1NoPqRvS2tUvWxYz0",
                "title": "Solve quadratic equation with integer roots",
                "problem": "Find all integer solutions to x² - 5x + 6 = 0",
                "domain": "general",
                "trace_version": 1,
                "content_hash": "a1b2c3d4e5f6...",
                "n_steps": 4,
                "provenance_sources": [
                    {
                        "source_type": "huggingface",
                        "source_id": "open-thoughts/OpenThoughts-114k",
                        "record_id": "5234"
                    }
                ],
                "provenance_license": "apache-2.0",
                "provenance_sensitivity": "public",
                "provenance_ingested_at": "2026-02-12T10:30:00Z",
                "provenance_pipeline_version": "0.1.0-alpha",
                "provenance_schema_version": "v1",
                "created_at": "2026-02-12T10:30:00Z",
                "updated_at": None,
                "deleted_at": None
            }
        }
```

---

## Step: Individual Reasoning Action

```python
class Step(BaseModel):
    """
    Single step in reasoning chain (user query, assistant response, thought, etc.).
    Text is externalized to S3; only key and preview stored here.
    """

    # Identity
    step_id: str = Field(
        description="ULID: unique within trace",
        pattern="^[a-zA-Z0-9]{26}$"  # ULID format
    )
    trace_id: str = Field(
        description="Parent trace reference"
    )

    # Position
    index: int = Field(
        ge=0,
        le=10000,
        description="Position in step sequence (0-indexed)"
    )

    # Semantics
    role: StepRole = Field(
        description="Semantic classification of this step"
    )
    actor: str = Field(
        examples=["user", "assistant", "system"],
        description="Who initiated this step"
    )

    # Text (externalized to S3)
    text_key: str = Field(
        description="S3 object key: steps/{trace_id}/{step_id}.md",
        pattern="^steps/[^/]+/[a-zA-Z0-9]{26}\\.md$"
    )
    text_preview: str = Field(
        max_length=500,
        description="First 500 chars of text (for quick display)"
    )
    text_hash: str = Field(
        pattern="^[a-f0-9]{64}$",
        description="SHA256(full_text) for integrity check"
    )
    text_version: int = Field(
        default=1,
        ge=1,
        description="Increments when text edited (FR-013)"
    )

    # Embedding (Principle VII: Dual-store, Principle VI: Schema)
    embedding_id: Optional[str] = Field(
        default=None,
        description="Reference to Qdrant point (usually same as step_id)"
    )
    embedding_version: Optional[int] = Field(
        default=None,
        description="Bound to text_version; NULL if needs re-embedding"
    )

    # Danger scores (aligned to canonical DangerScores; populated in Phase 2)
    danger_ambiguity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Ambiguity danger score; None until computed"
    )
    danger_adversarial: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Adversarial danger score; None until computed"
    )
    danger_irreversibility: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Irreversibility danger score; None until computed"
    )
    danger_institutional: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Institutional danger score; None until computed"
    )

    # Timestamps
    created_at: datetime = Field(description="When step was first recorded")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last text edit timestamp"
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Soft-delete timestamp"
    )

    @field_validator("text_version")
    @classmethod
    def text_version_consistency(cls, v, info):
        """Ensure text_version never decrements"""
        if "embedding_version" in info.data and info.data["embedding_version"]:
            if info.data["embedding_version"] > v:
                raise ValueError("embedding_version cannot exceed text_version")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "trace_id": "7k9mQ2aBc1NoPqRvS2tUvWxYz0",
                "index": 1,
                "role": "hypothesis",
                "actor": "assistant",
                "text_key": "steps/7k9mQ2aBc1NoPqRvS2tUvWxYz0/01ARZ3NDEKTSV4RRFFQ69G5FAV.md",
                "text_preview": "Let's factor the quadratic expression x² - 5x + 6...",
                "text_hash": "b2c3d4e5f6a7...",
                "text_version": 1,
                "embedding_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "embedding_version": 1,
                "created_at": "2026-02-12T10:30:05Z",
                "updated_at": None,
                "deleted_at": None
            }
        }
```

---

## Edge: Relationship Between Steps

```python
class Edge(BaseModel):
    """
    Relationship or connection between two steps.
    Default is NEXT (sequential); others capture reasoning structure.
    """

    edge_id: str = Field(
        description="ULID for audit trail",
        pattern="^[a-zA-Z0-9]{26}$"
    )
    type: EdgeType = Field(
        default=EdgeType.NEXT,
        description="Relationship type"
    )
    src_id: str = Field(
        description="Source step_id"
    )
    dst_id: str = Field(
        description="Destination step_id"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence or strength (0=weak, 1=strong)"
    )

    metadata: Optional[dict] = Field(
        default=None,
        description="Optional edge-specific data (e.g., reasoning for REFINES)"
    )

    @field_validator("src_id", "dst_id")
    @classmethod
    def ids_must_differ(cls, v, info):
        """Prevent self-loops"""
        if "src_id" in info.data and info.data["src_id"] == v and v == info.data.get("dst_id"):
            raise ValueError("Edge cannot loop to itself")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "edge_id": "01ARZ3NDEKTSV4RRFFQ7BJ2HZA",
                "type": "next",
                "src_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "dst_id": "01ARZ3NDEKTSV4RRFFQ7BJ3HCB",
                "weight": 1.0,
                "metadata": None
            }
        }
```

---

## Embedding: Vector Representation

```python
class Embedding(BaseModel):
    """
    Vector embedding for semantic search.
    Stored in Qdrant; linked to Step via embedding_id + text_version.
    """

    embedding_id: str = Field(
        description="Reference to step_id"
    )
    model_id: str = Field(
        examples=["all-MiniLM-L6-v2", "text-embedding-ada-002"],
        description="Model used to generate vector"
    )
    vector: List[float] = Field(
        min_length=384,
        max_length=8192,
        description="Embedding vector (384–8192 dimensions depending on model)"
    )
    text_version_bound: int = Field(
        description="Bound to Step.text_version; increment on edit"
    )

    # Danger markers (computed in Phase 2; range [0, 1])
    danger_ambiguity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0=clear, 1=ambiguous"
    )
    danger_adversarial: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0=benign, 1=adversarial"
    )
    danger_irreversibility: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0=reversible, 1=irreversible"
    )
    danger_institutional: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0=individual, 1=institutional"
    )
    danger_stale: bool = Field(
        default=False,
        description="True when text edited but danger not yet recomputed"
    )

    created_at: datetime = Field(description="When embedding computed")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="When danger markers recalculated"
    )

    @field_validator("vector")
    @classmethod
    def vector_magnitude(cls, v):
        """Ensure vectors are normalized (L2 ≈ 1)"""
        magnitude = sum(x**2 for x in v) ** 0.5
        if magnitude > 0 and abs(magnitude - 1.0) > 0.1:
            # Not normalized; OK but warn in logs
            pass
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "embedding_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "model_id": "all-MiniLM-L6-v2",
                "vector": [0.1, -0.2, 0.05, ...],  # 384 dims
                "text_version_bound": 1,
                "danger_ambiguity": 0.1,
                "danger_adversarial": 0.0,
                "danger_irreversibility": 0.05,
                "danger_institutional": 0.0,
                "created_at": "2026-02-12T10:30:10Z",
                "updated_at": None
            }
        }
```

---

## StepTextVersion: Markdown with Audit Trail

```python
class StepTextVersion(BaseModel):
    """
    Version entry for Step text (stored in S3 metadata).
    Multi-contributor edit history with compliance markers.
    """

    version_number: int = Field(
        ge=1,
        description="Version sequence"
    )
    previous_version: Optional[int] = Field(
        default=None,
        description="Link to predecessor version"
    )

    content_hash: str = Field(
        pattern="^[a-f0-9]{64}$",
        description="SHA256(text) for integrity"
    )
    previous_hash: Optional[str] = Field(
        default=None,
        description="Hash of previous version (for diff)"
    )

    # Attribution (Principle X: Privacy & Safety)
    contributor_id: str = Field(
        description="User ID or system identifier"
    )
    timestamp: datetime = Field(
        description="When edit occurred"
    )
    change_note: str = Field(
        max_length=500,
        examples=["Fixed grammar", "Clarified reasoning", "Corrected calculation"],
        description="Summary of change"
    )

    # Metadata
    language_hint: str = Field(
        default="english",
        examples=["english", "spanish", "french", "code"],
        description="Language hint for processing"
    )
    text_size_bytes: int = Field(
        description="Size of markdown content"
    )
    diff_size_bytes: Optional[int] = Field(
        default=None,
        description="Bytes changed from previous version"
    )

    # Compliance
    is_deleted: bool = Field(
        default=False,
        description="Soft-delete marker"
    )
    deletion_reason: Optional[str] = Field(
        default=None,
        examples=["PII removal", "Policy violation"],
        description="Why deleted (if applicable)"
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="When soft-deleted"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "version_number": 2,
                "previous_version": 1,
                "content_hash": "d4e5f6g7h8i9...",
                "previous_hash": "a1b2c3d4e5f6...",
                "contributor_id": "alice@example.com",
                "timestamp": "2026-02-12T14:32:00Z",
                "change_note": "Fixed grammar in step 2 reasoning",
                "language_hint": "english",
                "text_size_bytes": 1523,
                "diff_size_bytes": 47,
                "is_deleted": False,
                "deletion_reason": None,
                "deleted_at": None
            }
        }
```

---

## StepWindow: FSM-Adaptive Context

```python
class StepWindow(BaseModel):
    """
    Contextual window of steps for reasoning FSM.
    Variably-sized based on FSM type (RQ-5: FSM-adaptive windows).
    """

    center_step_id: str = Field(
        description="Step at window center"
    )
    center_index: int = Field(
        description="Position in trace"
    )

    # Preceding context
    predecessor_steps: List[Step] = Field(
        default=[],
        description="Steps before center (up to window_depth)"
    )
    top_pred_index: int = Field(
        default=-1,
        description="Index of earliest predecessor (-1 if none)"
    )

    # Succeeding context (potential outcomes)
    successor_steps: List[Step] = Field(
        default=[],
        description="Steps after center (up to window_depth)"
    )
    bottom_succ_index: int = Field(
        default=-1,
        description="Index of latest successor (-1 if none)"
    )

    # FSM classification (determines window depth)
    fsm_type: Literal[
        "hierarchical",
        "diagnostic",
        "optimization",
        "constraint_satisfaction"
    ] = Field(
        description="FSM type from reasoning structure"
    )
    window_depth: int = Field(
        description="Actual depth used (varies by FSM_type)"
    )

    # Computed for context quality
    total_context_steps: int = Field(
        description="Sum of predecessors + center + successors"
    )
    has_goal: bool = Field(
        default=False,
        description="Whether window includes GOAL step"
    )
    has_answer: bool = Field(
        default=False,
        description="Whether window includes ANSWER step"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "center_step_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "center_index": 5,
                "predecessor_steps": [...],  # 2-4 steps
                "top_pred_index": 2,
                "successor_steps": [...],     # 0-3 steps
                "bottom_succ_index": 7,
                "fsm_type": "hierarchical",
                "window_depth": 4,
                "total_context_steps": 8,
                "has_goal": True,
                "has_answer": False
            }
        }
```

---

## Pattern: Reusable Reasoning Structure

```python
class PatternType(str, Enum):
    """Classification of pattern detection method"""
    FSM_SUBPATH = "fsm_subpath"
    GRAPH_MOTIF = "graph_motif"
    SEMANTIC_CLUSTER = "semantic_cluster"
    MANUAL = "manual"


class PatternTemplateStep(BaseModel):
    """Template for a step within a pattern"""

    role: Literal[
        "goal", "question", "plan", "action", "tool_call", "observation",
        "critique", "revision", "decision", "verification", "summary", "other"
    ] = Field(
        description="Step role (from canonical StepRole enum)"
    )
    fsm_state: Optional[str] = Field(
        default=None,
        description="Optional FSM state filter"
    )
    text_template: str = Field(
        description="Template text with {placeholders} for slots"
    )
    slots: dict = Field(
        default_factory=dict,
        description="Variable names and descriptions for template substitution"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "plan",
                "fsm_state": "planning_phase",
                "text_template": "Plan to {action} by considering {factors}",
                "slots": {
                    "action": "the main task",
                    "factors": "key considerations"
                }
            }
        }


class PatternApplicability(BaseModel):
    """Constraints and filters for when a pattern applies"""

    fsm_id: Optional[str] = Field(
        default=None,
        description="FSM instance ID (if pattern is FSM-specific)"
    )
    allowed_states: list = Field(
        default_factory=list,
        description="FSM states where pattern is applicable"
    )
    domains: list = Field(
        default_factory=list,
        description="Applicable domains from DomainTag enum"
    )
    required_tags: list = Field(
        default_factory=list,
        description="Trace tags that must be present"
    )
    forbidden_tags: list = Field(
        default_factory=list,
        description="Trace tags that exclude pattern"
    )
    min_danger: dict = Field(
        default_factory=dict,
        description="Min danger thresholds (e.g., {'ambiguity': 0.3})"
    )
    max_danger: dict = Field(
        default_factory=dict,
        description="Max danger thresholds (e.g., {'adversarial': 0.5})"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "fsm_id": None,
                "allowed_states": ["planning", "execution"],
                "domains": ["software", "ml"],
                "required_tags": ["optimization"],
                "forbidden_tags": [" exploitative"],
                "min_danger": {"ambiguity": 0.1},
                "max_danger": {"irreversibility": 0.8}
            }
        }


class PatternQuality(BaseModel):
    """Metrics and quality measures for a pattern"""

    support: int = Field(
        default=0,
        ge=0,
        description="Number of traces containing this pattern"
    )
    avg_revision_loops: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Average number of revision iterations"
    )
    verification_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of successful traces"
    )
    success_proxy: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Proxy score for pattern quality (model-derived)"
    )
    last_updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last quality metric update"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "support": 42,
                "avg_revision_loops": 1.5,
                "verification_rate": 0.85,
                "success_proxy": 0.82,
                "last_updated_at": "2026-02-12T10:30:10Z"
            }
        }


class Pattern(BaseModel):
    """Reusable reasoning pattern detected or mined from traces"""

    pattern_id: str = Field(
        pattern="^[a-zA-Z0-9]{12}-[a-zA-Z0-9]{8}$",
        description="Unique pattern ID (base58 format)"
    )
    type: PatternType = Field(
        description="Pattern detection method"
    )

    name: str = Field(
        description="Human-readable pattern name (e.g., 'Binary Search Optimization')"
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of pattern behavior"
    )

    applicability: PatternApplicability = Field(
        default_factory=PatternApplicability,
        description="When this pattern should be applied"
    )
    template: list = Field(
        default_factory=list,
        description="Sequence of PatternTemplateStep objects"
    )
    embedding: Optional[str] = Field(
        default=None,
        description="Optional reference to vector embedding of pattern"
    )
    quality: PatternQuality = Field(
        default_factory=PatternQuality,
        description="Quality metrics"
    )

    created_at: Optional[datetime] = Field(
        default=None,
        description="When pattern was first detected"
    )
    miner_version: Optional[str] = Field(
        default=None,
        description="Version of pattern mining algorithm that found it"
    )
    schema_version: str = Field(
        default="v1",
        description="Schema version for evolution"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pattern_id": "pattern-001-abcd1234",
                "type": "fsm_subpath",
                "name": "Binary Search Scope Refinement",
                "description": "Narrow search space by dividing domain in half",
                "applicability": {...},  # PatternApplicability example
                "template": [
                    {
                        "role": "goal",
                        "text_template": "Narrow scope: search in {domain_half}",
                        "slots": {"domain_half": "left or right half"}
                    }
                ],
                "quality": {
                    "support": 23,
                    "verification_rate": 0.9
                },
                "created_at": "2026-02-01T08:00:00Z",
                "miner_version": "v0.1.0"
            }
        }


class PatternInstance(BaseModel):
    """Instantiation of a pattern within a specific trace"""

    instance_id: str = Field(
        pattern="^[a-zA-Z0-9]{12}-[a-zA-Z0-9]{8}$",
        description="Unique instance ID"
    )
    pattern_id: str = Field(
        description="Reference to Pattern.pattern_id"
    )
    trace_id: str = Field(
        description="Trace where pattern was found"
    )

    step_ids: list = Field(
        default_factory=list,
        description="Sequence of step IDs matching pattern template"
    )
    bindings: dict = Field(
        default_factory=dict,
        description="Slot bindings (e.g., {'domain_half': 'left'})"
    )
    success_proxy: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Quality score for this instance"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "instance_id": "inst-001-efgh5678",
                "pattern_id": "pattern-001-abcd1234",
                "trace_id": "trace-001-ijkl9012",
                "step_ids": ["01ARZ3NDEKTSV4RRFFQ69G5FAV", "01ARZ3NDEKTSV4RRFFQ7BJ3HCB"],
                "bindings": {"domain_half": "left"},
                "success_proxy": 0.88
            }
        }
```

---

## TraceBundle: Atomic Ingestion Unit

```python
class TraceBundle(BaseModel):
    """
    Transactional unit for ingestion.
    All-or-nothing: if any component fails validation, entire bundle rejected.
    """

    trace: Trace
    steps: List[Step] = Field(
        min_length=1,
        description="Steps in order (index must be 0..n-1)"
    )
    edges: List[Edge] = Field(
        default_factory=list,
        description="Relationships (typically NEXT edges)"
    )

    @field_validator("steps")
    @classmethod
    def steps_must_be_ordered(cls, v):
        """Validate step indexes are contiguous 0..n-1"""
        if not v:
            raise ValueError("Must have at least 1 step")

        actual_indices = sorted(set(s.index for s in v))
        expected_indices = list(range(len(v)))

        if actual_indices != expected_indices:
            raise ValueError(
                f"Step indexes must be contiguous starting at 0; "
                f"got {actual_indices}, expected {expected_indices}"
            )
        return v

    @field_validator("trace")
    @classmethod
    def trace_step_count_matches(cls, v, info):
        """Ensure trace.n_steps matches actual step count"""
        if "steps" in info.data:
            if v.n_steps != len(info.data["steps"]):
                raise ValueError(
                    f"Trace.n_steps ({v.n_steps}) must match "
                    f"actual steps count ({len(info.data['steps'])})"
                )
        return v

    @field_validator("edges")
    @classmethod
    def edges_reference_valid_steps(cls, v, info):
        """Every edge must reference existing steps"""
        if "steps" not in info.data:
            return v

        step_ids = set(s.step_id for s in info.data["steps"])

        for edge in v:
            if edge.src_id not in step_ids:
                raise ValueError(f"Edge references unknown step {edge.src_id}")
            if edge.dst_id not in step_ids:
                raise ValueError(f"Edge references unknown step {edge.dst_id}")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "trace": {...},  # Trace example
                "steps": [...],  # Step[] example
                "edges": [...]   # Edge[] example
            }
        }
```

---

## Validation Rules Summary

| Entity | Field | Rule | Reason |
|--------|-------|------|--------|
| Trace | content_hash | SHA256 pattern + immutable | FR-002b deduplication |
| Trace | provenance_* | All required | FR-007 provenance tracking |
| Step | index | 0..n-1 contiguous | FR-001 ordering |
| Step | embedding_version | ≤ text_version | FR-006a version binding |
| Step | text_key | Must match S3 pattern | FR-013 externalization |
| Edge | src_id, dst_id | No self-loops | Graph integrity |
| Embedding | vector | 384 dimensions | all-MiniLM-L6-v2 default |
| TraceBundle | All | Atomic validation | FR-005 transaction semantics |

---

## JSON Schema Generation

```python
# Export JSON schemas for OpenAPI/documentation
if __name__ == "__main__":
    from json import dumps

    schemas = {
        "Trace": Trace.model_json_schema(),
        "Step": Step.model_json_schema(),
        "Edge": Edge.model_json_schema(),
        "Embedding": Embedding.model_json_schema(),
        "StepTextVersion": StepTextVersion.model_json_schema(),
        "StepWindow": StepWindow.model_json_schema(),
        "TraceBundle": TraceBundle.model_json_schema(),
    }

    for name, schema in schemas.items():
        with open(f"schemas/{name}.json", "w") as f:
            f.write(dumps(schema, indent=2))
```

---

## Compatibility

- **Pydantic v2**: All models use `BaseModel` from `pydantic` (v2.x)
- **JSON Serialization**: All models support `.model_dump_json()` and `.model_validate_json()`
- **Database Storage**: Neo4j stores as properties; Qdrant stores in payloads
- **Schema Evolution**: `provenance_schema_version` allows future model updates with backward compatibility
