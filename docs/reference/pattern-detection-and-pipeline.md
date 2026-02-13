# Pattern Detection & Pipeline

> Auto-detection of control-pattern operators from raw text traces, motif mining, corpus-level aggregation, store writers (Neo4j + Qdrant), and flexible embedding pipeline.
>
> **Note on model re-declarations:** Each module below defines its own local models (`StepOp`, `Motif`, `Pattern`, etc.) for self-contained readability. In production, these should import from or align to [Canonical Schemas](canonical-schemas.md). Where field shapes differ, the canonical schema is authoritative.
>
> For the pattern taxonomy these operators belong to, see [Control Pattern Taxonomy](../domain/control-pattern-taxonomy.md). For the schemas these modules emit, see [Canonical Schemas](canonical-schemas.md). For Pydantic v2 implementations with validators, see [Feature Spec Data Model](/specs/001-canonical-schema-implementation/data-model.md). For storage layout, see [Storage Mapping](storage-mapping.md). For Qdrant collection setup, see [Qdrant Setup](qdrant-setup.md).

---

## Overview

Four modules, run in sequence:

1. **`op_detection_and_mining`** — Step-level operator tagging + single-trace motif mining
2. **`corpus_pattern_aggregation`** — Merge identical patterns across traces, assign stable IDs
3. **`store_writers`** — Upsert patterns + instances to Neo4j and Qdrant
4. **`embedding_pipeline_flexible`** — Dev (384-dim local) / prod (cloud) embedding + Qdrant vector upsert

---

## Operator keyword signals (rule-based, pre-ML)

| Operator | Trigger keywords |
|----------|-----------------|
| `ASSERT` | "we know", "it is", "this means", "the cause is", "assume", "constraint", "requirement", "goal" |
| `ASK` | "?", wh-words ("what", "how", "why", …), modal questions |
| `OBSERVE` | "observe", "we see", "results show", "logs show/indicate", "metric", "output" |
| `BRANCH` | "if", "else", "otherwise", "unless", "in case" |
| `SELECT` | "choose", "pick", "select", "rank", "prioritize", "top-k", "shortlist", "argmax", "tradeoff" |
| `ITERATE` | "iterate", "loop", "repeat", "again", "refine", "until", "converge" |
| `EXECUTE` | "run", "execute", "deploy", "apply", "call", "implement", "ship", "roll out" |
| `UPDATE` | "update belief", "therefore likely", "increase confidence", "now think" |
| `GUARD` | "only if", "must", "required", "blocked", "before we" |
| `ESCALATE` | "legal/team/board needs", "sign-off", "approve", "escalate" |
| `HALT` | "stop", "cannot proceed", "done", "conclusion" |

### Chunk-level motifs (sliding window, k=5–8 steps)

| Motif | Operator sequence |
|-------|-------------------|
| Debug loop | `ASSERT(symptom) → BRANCH(hypothesis) → EXECUTE(test) → OBSERVE → UPDATE → (ITERATE)` |
| Clarify | Many `ASK` steps early + missing metrics/constraints |
| Verify | `ASSERT(claim) → ASSERT(assumption) → SELECT(tests) → EXECUTE(test) → OBSERVE → UPDATE(confidence)` |

### Upgrade path

1. **Structured extraction** — Extract artifacts (Goal, Metric, Constraint, Option, Hypothesis, Risk, Stakeholder) via regex + small LLM slot-fill prompts
2. **Sequence tagger** — Train token/step classifier: inputs = step text embedding + artifact flags + previous op/state → outputs = `op_type`, `fsm_state`
3. **Motif mining** — Mine frequent subsequences of `(op_type, fsm_state)` and graph motifs using `SUPPORTS`/`REFUTES`/`REVISES` edges

---

## Module 1: `op_detection_and_mining.py`

```python
"""
op_detection_and_mining.py (Pydantic v2)

Minimal, shippable MVP:
- Step-level operator detection from raw text (rules + scores + evidence spans)
- Simple FSM-state hinting (light heuristics)
- Motif mining over operator n-grams
- Emits Pattern + PatternInstance objects compatible with canonical schema

Requires: pydantic>=2
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class OpType(str, Enum):
    ASSERT = "ASSERT"
    ASK = "ASK"
    OBSERVE = "OBSERVE"
    BRANCH = "BRANCH"
    SELECT = "SELECT"
    ITERATE = "ITERATE"
    UPDATE = "UPDATE"
    EXECUTE = "EXECUTE"
    GUARD = "GUARD"
    HALT = "HALT"
    ESCALATE = "ESCALATE"
    OTHER = "OTHER"


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


class PatternType(str, Enum):
    FSM_SUBPATH = "fsm_subpath"
    SEMANTIC_CLUSTER = "semantic_cluster"
    GRAPH_MOTIF = "graph_motif"
    MANUAL = "manual"


# --- Pydantic models ---

class EvidenceSpan(BaseModel):
    pattern: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    match: str

    @field_validator("end")
    @classmethod
    def _end_gte_start(cls, v: int, info) -> int:
        start = info.data.get("start", 0)
        if v < start:
            raise ValueError("end must be >= start")
        return v


class OpTag(BaseModel):
    op_type: OpType
    score: float = Field(ge=0.0, le=1.0)
    evidence: List[EvidenceSpan] = Field(default_factory=list)


class StepAnnotation(BaseModel):
    step_id: str
    text: str
    op_tags: List[OpTag] = Field(default_factory=list)
    primary_op: OpType = OpType.OTHER
    role: StepRole = StepRole.OTHER
    fsm_state: Optional[FSMState] = None
    debug: Dict[str, Any] = Field(default_factory=dict)


class PatternTemplateStep(BaseModel):
    role: StepRole
    fsm_state: Optional[FSMState] = None
    text_template: str
    slots: Dict[str, str] = Field(default_factory=dict)


class PatternApplicability(BaseModel):
    fsm_state: Optional[FSMState] = None
    allowed_states: List[FSMState] = Field(default_factory=list)
    required_ops: List[OpType] = Field(default_factory=list)


class PatternQuality(BaseModel):
    support: int = Field(default=0, ge=0)


class Pattern(BaseModel):
    pattern_id: str
    type: PatternType
    name: str
    description: Optional[str] = None
    applicability: PatternApplicability = Field(default_factory=PatternApplicability)
    template: List[PatternTemplateStep] = Field(default_factory=list)
    quality: PatternQuality = Field(default_factory=PatternQuality)
    signature: str


class PatternInstance(BaseModel):
    instance_id: str
    pattern_id: str
    trace_id: str
    step_ids: List[str] = Field(default_factory=list)
    bindings: Dict[str, Any] = Field(default_factory=dict)


# --- Rules (regex) for op detection ---

_RULES: Dict[OpType, List[Tuple[str, re.Pattern, float]]] = {
    OpType.ASK: [
        ("qmark", re.compile(r"\?\s*$"), 0.7),
        ("wh_word", re.compile(r"^\s*(what|how|why|when|where|who|which)\b", re.I), 0.6),
        ("modal_q", re.compile(r"^\s*(can|could|should|would|may)\b.*\?\s*$", re.I), 0.7),
    ],
    OpType.BRANCH: [
        ("if_else", re.compile(r"\b(if|else|otherwise|unless|in case)\b", re.I), 0.6),
        ("ternary_like", re.compile(r"\b(either|or)\b.*\b(either|or)\b", re.I), 0.4),
    ],
    OpType.SELECT: [
        ("choose", re.compile(r"\b(choose|pick|select|rank|prioriti[sz]e|top[- ]?k|shortlist|argmax)\b", re.I), 0.6),
        ("tradeoff", re.compile(r"\b(trade[- ]?off|pros? and cons|score(?:card)?|criteria|weight)\b", re.I), 0.5),
    ],
    OpType.ITERATE: [
        ("iterate", re.compile(r"\b(iterate|loop|repeat|again|refine|until|converge|keep trying)\b", re.I), 0.6),
    ],
    OpType.EXECUTE: [
        ("do_action", re.compile(r"\b(run|execute|deploy|apply|call|query|build|implement|ship|roll out)\b", re.I), 0.5),
        ("imperative", re.compile(r"^\s*(run|execute|deploy|apply|do|try|test)\b", re.I), 0.5),
    ],
    OpType.OBSERVE: [
        ("observe", re.compile(r"\b(observe|we see|results show|logs (show|indicate)|metric(s)?|output)\b", re.I), 0.6),
        ("numbers", re.compile(r"\b(\d+(\.\d+)?%|\d+(\.\d+)?\s*(ms|s|sec|fps|gb|mb|w|€|\$))\b", re.I), 0.4),
    ],
    OpType.UPDATE: [
        ("update", re.compile(r"\b(update|therefore|so|thus|likely|confidence|posterior|now think)\b", re.I), 0.5),
        ("revise_belief", re.compile(r"\b(i (now )?believe|i think now|we conclude|points to)\b", re.I), 0.6),
    ],
    OpType.GUARD: [
        ("must_before", re.compile(r"\b(only if|must|required|before we|blocked|cannot proceed until)\b", re.I), 0.7),
    ],
    OpType.HALT: [
        ("stop", re.compile(r"\b(stop|cannot proceed|no way to|done|conclusion)\b", re.I), 0.6),
    ],
    OpType.ESCALATE: [
        ("escalate", re.compile(r"\b(escalate|sign[- ]?off|approval|legal team|board|regulator|compliance)\b", re.I), 0.6),
    ],
    OpType.ASSERT: [
        ("assert", re.compile(r"\b(we know|it is|this means|the cause is|assume|constraint|requirement|goal)\b", re.I), 0.4),
    ],
}

_ROLE_HINTS: List[Tuple[StepRole, re.Pattern]] = [
    (StepRole.QUESTION, re.compile(r"\?\s*$")),
    (StepRole.PLAN, re.compile(r"\b(plan|steps?:|approach|we will|roadmap)\b", re.I)),
    (StepRole.DECISION, re.compile(r"\b(decide|decision|choose|pick|we'll go with)\b", re.I)),
    (StepRole.VERIFICATION, re.compile(r"\b(verify|validate|test|falsif|replicat|check)\b", re.I)),
    (StepRole.OBSERVATION, re.compile(r"\b(results show|logs|metric|output|observ(e|ation))\b", re.I)),
    (StepRole.ACTION, re.compile(r"\b(run|execute|deploy|apply|implement)\b", re.I)),
    (StepRole.SUMMARY, re.compile(r"\b(summary|in short|overall)\b", re.I)),
]

_STATE_HINTS: List[Tuple[FSMState, re.Pattern]] = [
    (FSMState.S1_CLARIFY, re.compile(r"\?\s*$|\bclarify|define|scope\b", re.I)),
    (FSMState.S2_MODEL, re.compile(r"\bmodel|hypothesis|cause|assumption|threat model\b", re.I)),
    (FSMState.S3_PLAN, re.compile(r"\bplan|steps?:|approach|option(s)?\b", re.I)),
    (FSMState.S4_EXECUTE, re.compile(r"\b(run|execute|deploy|apply|implement|call)\b", re.I)),
    (FSMState.S5_OBSERVE, re.compile(r"\b(logs|results show|output|metric)\b", re.I)),
    (FSMState.S6_EVALUATE, re.compile(r"\b(evaluate|compare|trade[- ]?off|pros? and cons|score)\b", re.I)),
    (FSMState.S7_DECIDE, re.compile(r"\b(decide|choose|pick|go with)\b", re.I)),
    (FSMState.S8_HARDEN, re.compile(r"\b(monitor|alert|runbook|rollback|guardrail|productionize)\b", re.I)),
    (FSMState.S9_CLOSE, re.compile(r"\b(done|conclusion|final)\b", re.I)),
]


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def detect_ops(text: str) -> List[OpTag]:
    """Rule-based multi-label op detection with evidence spans."""
    t = text or ""
    out: List[OpTag] = []

    for op, rules in _RULES.items():
        evid: List[EvidenceSpan] = []
        score = 0.0
        for name, pat, w in rules:
            for m in pat.finditer(t):
                evid.append(EvidenceSpan(
                    pattern=f"{op.value}:{name}", start=m.start(), end=m.end(), match=m.group(0)))
                score += w
        if evid:
            out.append(OpTag(op_type=op, score=min(score, 1.0), evidence=evid))

    if not out:
        out.append(OpTag(op_type=OpType.OTHER, score=0.2, evidence=[]))

    out.sort(key=lambda x: x.score, reverse=True)
    return out


def choose_primary_op(op_tags: List[OpTag]) -> OpType:
    if not op_tags:
        return OpType.OTHER
    for preferred in (OpType.GUARD, OpType.ESCALATE, OpType.HALT):
        for t in op_tags:
            if t.op_type == preferred and t.score >= 0.6:
                return preferred
    return op_tags[0].op_type


def infer_role(text: str) -> StepRole:
    for role, pat in _ROLE_HINTS:
        if pat.search(text or ""):
            return role
    return StepRole.OTHER


def infer_state(text: str) -> Optional[FSMState]:
    for st, pat in _STATE_HINTS:
        if pat.search(text or ""):
            return st
    return None


def annotate_step(step_id: str, text: str) -> StepAnnotation:
    op_tags = detect_ops(text)
    primary = choose_primary_op(op_tags)
    role = infer_role(text)
    state = infer_state(text)
    return StepAnnotation(
        step_id=step_id, text=text, op_tags=op_tags, primary_op=primary,
        role=role, fsm_state=state,
        debug={"primary_op_reason":
               "priority_override" if primary in {OpType.GUARD, OpType.ESCALATE, OpType.HALT}
               else "max_score"},
    )


# --- Motif mining (n-gram over ops) ---

@dataclass(frozen=True)
class MotifKey:
    ops: Tuple[OpType, ...]
    states: Tuple[Optional[FSMState], ...]


def motif_signature(ops: Sequence[OpType], states: Sequence[Optional[FSMState]]) -> str:
    return " | ".join(f"{op.value}:{(st.value if st else 'NA')}" for op, st in zip(ops, states))


def mine_motifs(
    trace_id: str,
    annotated_steps: Sequence[StepAnnotation],
    n: int = 4,
    min_support: int = 3,
    stride: int = 1,
) -> Tuple[List[Pattern], List[PatternInstance]]:
    """Mines frequent operator-state n-grams as FSM_SUBPATH patterns."""
    if n <= 1:
        raise ValueError("n must be >= 2")

    ops = [s.primary_op for s in annotated_steps]
    sts = [s.fsm_state for s in annotated_steps]
    step_ids = [s.step_id for s in annotated_steps]

    motif_positions: Dict[MotifKey, List[int]] = defaultdict(list)
    for i in range(0, len(annotated_steps) - n + 1, stride):
        key = MotifKey(ops=tuple(ops[i:i+n]), states=tuple(sts[i:i+n]))
        motif_positions[key].append(i)

    kept = {k: pos for k, pos in motif_positions.items() if len(pos) >= min_support}

    patterns: List[Pattern] = []
    instances: List[PatternInstance] = []

    _OP_TO_ROLE = {
        OpType.ASK: StepRole.QUESTION, OpType.EXECUTE: StepRole.ACTION,
        OpType.OBSERVE: StepRole.OBSERVATION, OpType.SELECT: StepRole.DECISION,
        OpType.UPDATE: StepRole.CRITIQUE, OpType.GUARD: StepRole.VERIFICATION,
        OpType.BRANCH: StepRole.DECISION, OpType.ITERATE: StepRole.PLAN,
        OpType.ASSERT: StepRole.OTHER, OpType.HALT: StepRole.SUMMARY,
        OpType.ESCALATE: StepRole.DECISION, OpType.OTHER: StepRole.OTHER,
    }

    for key, positions in kept.items():
        sig = motif_signature(key.ops, key.states)
        pid = f"pat_{_hash(sig)}"

        template_steps = [
            PatternTemplateStep(
                role=_OP_TO_ROLE.get(op, StepRole.OTHER),
                fsm_state=st,
                text_template=f"{op.value} step",
            )
            for op, st in zip(key.ops, key.states)
        ]

        pat = Pattern(
            pattern_id=pid, type=PatternType.FSM_SUBPATH,
            name=f"Motif: {sig}",
            description="Frequent operator/state subsequence (n-gram) mined from traces.",
            applicability=PatternApplicability(
                fsm_state=key.states[-1] if key.states else None,
                allowed_states=[st for st in key.states if st is not None],
                required_ops=list(key.ops),
            ),
            template=template_steps,
            quality=PatternQuality(support=len(positions)),
            signature=sig,
        )
        patterns.append(pat)

        for pos in positions:
            inst_id = f"inst_{_hash(trace_id + pid + str(pos))}"
            instances.append(PatternInstance(
                instance_id=inst_id, pattern_id=pid, trace_id=trace_id,
                step_ids=step_ids[pos:pos+n],
            ))

    return patterns, instances


def annotate_trace(trace_id: str, steps: List[Tuple[str, str]]) -> List[StepAnnotation]:
    """steps: list[(step_id, text)]"""
    return [annotate_step(step_id=sid, text=txt) for sid, txt in steps]
```

### Pipeline integration

During ingestion, after creating `Step` objects:

1. Run `annotate_step(step_id, text)` and store `step.properties["op_tags"]`, `step.properties["primary_op"]` and weak labels for `step.role` / `step.fsm_state`
2. Run `mine_motifs(trace_id, annotated_steps, n=4, min_support=K)` per trace
3. Call `attach_signature_to_instances(patterns, instances)` so each instance carries `bindings["_signature"]`
4. Aggregate across traces by `Pattern.signature` to get global support

---

## Module 2: `corpus_pattern_aggregation.py`

```python
"""
corpus_pattern_aggregation.py (Pydantic v2)

Corpus-level motif aggregation:
- Merge identical Pattern.signature across many traces
- Assign stable pattern_id (hash of signature)
- Update PatternQuality.support (global)
- Emit Neo4j upsert payloads + Qdrant payload metadata

Requires: pydantic>=2
"""

from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field


class PatternQuality(BaseModel):
    support: int = Field(default=0, ge=0)


class PatternApplicability(BaseModel):
    fsm_state: Optional[str] = None
    allowed_states: List[str] = Field(default_factory=list)
    required_ops: List[str] = Field(default_factory=list)


class PatternTemplateStep(BaseModel):
    role: str
    fsm_state: Optional[str] = None
    text_template: str
    slots: Dict[str, str] = Field(default_factory=dict)


class Pattern(BaseModel):
    pattern_id: str
    type: str
    name: str
    description: Optional[str] = None
    applicability: PatternApplicability = Field(default_factory=PatternApplicability)
    template: List[PatternTemplateStep] = Field(default_factory=list)
    quality: PatternQuality = Field(default_factory=PatternQuality)
    signature: str


class PatternInstance(BaseModel):
    instance_id: str
    pattern_id: str
    trace_id: str
    step_ids: List[str] = Field(default_factory=list)
    bindings: Dict[str, Any] = Field(default_factory=dict)


# --- Stable IDs ---

def stable_pattern_id(signature: str, prefix: str = "pat") -> str:
    h = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def stable_instance_id(trace_id: str, pattern_id: str, start_step_id: str, prefix: str = "inst") -> str:
    seed = f"{trace_id}|{pattern_id}|{start_step_id}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


# --- Aggregation ---

@dataclass
class AggregationStats:
    total_patterns_seen: int = 0
    unique_signatures: int = 0
    total_instances: int = 0


class AggregatedPattern(BaseModel):
    pattern: Pattern
    instances: List[PatternInstance] = Field(default_factory=list)


def aggregate_patterns_corpus(
    per_trace_patterns: Iterable[Sequence[Pattern]],
    per_trace_instances: Iterable[Sequence[PatternInstance]],
) -> Tuple[List[AggregatedPattern], AggregationStats]:
    """Merge patterns by signature across the corpus."""
    by_sig: Dict[str, AggregatedPattern] = {}
    stats = AggregationStats()

    for patterns in per_trace_patterns:
        for p in patterns:
            stats.total_patterns_seen += 1
            sig = p.signature
            if sig not in by_sig:
                pid = stable_pattern_id(sig)
                proto = p.model_copy(deep=True)
                proto.pattern_id = pid
                proto.quality.support = 0
                by_sig[sig] = AggregatedPattern(pattern=proto, instances=[])

    for instances in per_trace_instances:
        for inst in instances:
            stats.total_instances += 1
            sig = inst.bindings.get("_signature")
            if not sig or sig not in by_sig:
                continue

            stable_pid = by_sig[sig].pattern.pattern_id
            stable_inst = inst.model_copy(deep=True)
            stable_inst.pattern_id = stable_pid
            stable_inst.instance_id = stable_instance_id(
                trace_id=stable_inst.trace_id,
                pattern_id=stable_pid,
                start_step_id=stable_inst.step_ids[0] if stable_inst.step_ids else "na",
            )
            by_sig[sig].instances.append(stable_inst)

    for agg in by_sig.values():
        agg.pattern.quality.support = len(agg.instances)

    stats.unique_signatures = len(by_sig)
    return list(by_sig.values()), stats


def attach_signature_to_instances(
    patterns: Sequence[Pattern],
    instances: Sequence[PatternInstance],
) -> List[PatternInstance]:
    """Ensures each instance.bindings['_signature'] exists so corpus aggregation can join."""
    pid_to_sig = {p.pattern_id: p.signature for p in patterns}
    out: List[PatternInstance] = []
    for inst in instances:
        sig = pid_to_sig.get(inst.pattern_id)
        if sig:
            inst2 = inst.model_copy(deep=True)
            inst2.bindings = dict(inst2.bindings)
            inst2.bindings["_signature"] = sig
            out.append(inst2)
        else:
            out.append(inst)
    return out


# --- Neo4j upsert payloads ---

def to_neo4j_pattern_upserts(aggregated: Sequence[AggregatedPattern]) -> Dict[str, Any]:
    patterns_payload: List[Dict[str, Any]] = []
    instances_payload: List[Dict[str, Any]] = []

    for agg in aggregated:
        p = agg.pattern
        patterns_payload.append({
            "pattern_id": p.pattern_id,
            "props": {
                "pattern_id": p.pattern_id,
                "type": p.type,
                "name": p.name,
                "description": p.description,
                "signature": p.signature,
                "applicability_json": p.applicability.model_dump_json(),
                "template_json": json.dumps([ts.model_dump() for ts in p.template]),
                "quality_support": p.quality.support,
                "schema_version": "v1",
            },
        })

        for inst in agg.instances:
            bindings_json = json.dumps(inst.bindings) if inst.bindings else "{}"
            for j, step_id in enumerate(inst.step_ids or []):
                props = {}
                if j == 0:
                    props["bindings_json"] = bindings_json
                    props["step_ids_json"] = json.dumps(inst.step_ids)
                instances_payload.append({
                    "instance_id": inst.instance_id,
                    "step_id": step_id,
                    "pattern_id": p.pattern_id,
                    "props": props,
                })

    return {"patterns": patterns_payload, "pattern_instances": instances_payload}


# --- Qdrant payload metadata ---

def to_qdrant_pattern_points_payload(aggregated: Sequence[AggregatedPattern]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for agg in aggregated:
        p = agg.pattern
        app = p.applicability
        points.append({
            "id": p.pattern_id,
            "payload": {
                "pattern_id": p.pattern_id,
                "type": p.type,
                "name": p.name,
                "description": p.description or "",
                "fsm_id": None,
                "allowed_states": app.allowed_states,
                "domains": [],
                "required_tags": [],
                "forbidden_tags": [],
                "quality_support": p.quality.support,
                "quality_success_proxy": None,
                "miner_version": "miner_v1",
                "schema_version": "v1",
                "signature": p.signature,
                "required_ops": app.required_ops,
            },
        })
    return points
```

---

## Module 3: `store_writers.py`

```python
"""
store_writers.py

End-to-end writers:
- Neo4j: upsert patterns + create Step-[:INSTANCE_OF]->Pattern edges
- Qdrant: upsert pattern points (payload now; vectors optional)

Dependencies: neo4j, qdrant-client
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from neo4j import GraphDatabase, Driver
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


NEO4J_UPSERT_PATTERNS = """
UNWIND $patterns AS p
MERGE (pt:Pattern {pattern_id: p.pattern_id})
SET pt += p.props
"""

NEO4J_LINK_STEP_INSTANCE_OF_PATTERN = """
UNWIND $pattern_instances AS i
MATCH (st:Step {step_id: i.step_id})
MATCH (pt:Pattern {pattern_id: i.pattern_id})
MERGE (st)-[r:INSTANCE_OF {instance_id: i.instance_id}]->(pt)
SET r += i.props
"""


class Neo4jWriter:
    def __init__(self, uri: str, user: str, password: str, database: Optional[str] = None) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def upsert_patterns_and_instances(
        self,
        patterns_payload: List[Dict[str, Any]],
        pattern_instances_payload: List[Dict[str, Any]],
        batch_size: int = 2000,
    ) -> None:
        with self._driver.session(database=self._database) as session:
            for i in range(0, len(patterns_payload), batch_size):
                session.run(NEO4J_UPSERT_PATTERNS, patterns=patterns_payload[i:i+batch_size])
            for i in range(0, len(pattern_instances_payload), batch_size):
                session.run(NEO4J_LINK_STEP_INSTANCE_OF_PATTERN,
                            pattern_instances=pattern_instances_payload[i:i+batch_size])


class QdrantWriter:
    def __init__(self, url: str, api_key: Optional[str] = None) -> None:
        self._client = QdrantClient(url=url, api_key=api_key)

    def upsert_pattern_payloads(
        self,
        collection: str,
        points_payload: Sequence[Dict[str, Any]],
        vectors: Optional[Dict[str, List[float]]] = None,
        batch_size: int = 256,
    ) -> None:
        batch: List[PointStruct] = []
        for p in points_payload:
            pid = str(p["id"])
            payload = dict(p.get("payload") or {})
            if vectors is None:
                pt = PointStruct(id=pid, vector=[], payload=payload)
            else:
                vec = vectors.get(pid)
                if vec is None:
                    raise ValueError(f"Missing vector for pattern_id={pid}")
                pt = PointStruct(id=pid, vector=vec, payload=payload)
            batch.append(pt)
            if len(batch) >= batch_size:
                self._client.upsert(collection_name=collection, points=batch)
                batch = []
        if batch:
            self._client.upsert(collection_name=collection, points=batch)


def write_outputs(
    neo4j_uri: str, neo4j_user: str, neo4j_password: str,
    qdrant_url: str,
    neo_payload: Dict[str, Any],
    qdrant_points: List[Dict[str, Any]],
    qdrant_collection: str = "patterns",
    neo4j_database: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
) -> None:
    neo = Neo4jWriter(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)
    try:
        neo.upsert_patterns_and_instances(
            patterns_payload=neo_payload.get("patterns", []),
            pattern_instances_payload=neo_payload.get("pattern_instances", []),
        )
    finally:
        neo.close()

    qd = QdrantWriter(url=qdrant_url, api_key=qdrant_api_key)
    qd.upsert_pattern_payloads(collection=qdrant_collection, points_payload=qdrant_points, vectors=None)
```

---

## Module 4: `embedding_pipeline_flexible.py`

```python
"""
embedding_pipeline_flexible.py

Flexible embedding pipeline:
- Dev: local small model (sentence-transformers, 384-dim)
- Prod: cloud embeddings (any provider) OR bigger local
- Same interface + same downstream writers

Dependencies: pydantic, neo4j, qdrant-client, sentence-transformers, numpy
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class Pattern(BaseModel):
    pattern_id: str
    type: str
    name: str
    description: Optional[str] = None
    signature: str
    applicability_json: Optional[str] = None
    template_json: Optional[str] = None
    quality_support: int = 0


# --- Embedding provider interface ---

class EmbeddingProvider(Protocol):
    @property
    def dim(self) -> int: ...
    @property
    def model_name(self) -> str: ...
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]: ...


# --- Local provider (dev) ---

class LocalSentenceTransformersProvider:
    """Typical 384-dim: sentence-transformers/all-MiniLM-L6-v2"""
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        test = self._model.encode(["test"], normalize_embeddings=True)
        self._dim = int(test.shape[1])

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        arr = self._model.encode(list(texts), normalize_embeddings=True)
        return arr.astype(np.float32).tolist()


# --- Cloud provider (prod) stub ---

class CloudEmbeddingProvider:
    """Implement this wrapper around your production embedding service."""
    def __init__(self, model_name: str, dim: int) -> None:
        self._model_name = model_name
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        raise NotImplementedError("Wire to your cloud embedding API here.")


# --- Pattern text rendering ---

def render_pattern_text(p: Pattern) -> str:
    """Deterministic canonical string; keeps vectors stable across runs."""
    parts = [f"NAME: {p.name}", f"TYPE: {p.type}", f"SIGNATURE: {p.signature}"]
    if p.description:
        parts.append(f"DESC: {p.description}")
    if p.applicability_json:
        parts.append(f"APPLICABILITY: {p.applicability_json}")
    if p.template_json:
        parts.append(f"TEMPLATE: {p.template_json}")
    parts.append(f"SUPPORT: {p.quality_support}")
    return "\n".join(parts)


# --- Qdrant helpers ---

def ensure_qdrant_collection(
    client: QdrantClient, collection_name: str, dim: int,
    distance: Distance = Distance.COSINE,
) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=distance),
    )


def upsert_patterns_qdrant(
    client: QdrantClient, collection_name: str,
    patterns: Sequence[Pattern], vectors: Sequence[Sequence[float]],
    embed_model: str, embed_dim: int, batch_size: int = 256,
) -> None:
    assert len(patterns) == len(vectors)
    points: List[PointStruct] = []
    for p, v in zip(patterns, vectors):
        payload = {
            "pattern_id": p.pattern_id, "type": p.type, "name": p.name,
            "description": p.description or "", "signature": p.signature,
            "quality_support": p.quality_support,
            "embedding_model": embed_model, "embedding_dim": embed_dim,
            "schema_version": "v1",
        }
        points.append(PointStruct(id=p.pattern_id, vector=list(v), payload=payload))
        if len(points) >= batch_size:
            client.upsert(collection_name=collection_name, points=points)
            points = []
    if points:
        client.upsert(collection_name=collection_name, points=points)


# --- End-to-end: embed + upsert ---

@dataclass
class EmbedConfig:
    mode: str  # "dev" | "prod"
    qdrant_collection_dev: str = "patterns_dev_384"
    qdrant_collection_prod: str = "patterns_prod"
    local_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    prod_model_name: str = "your-prod-embedding-model"
    prod_dim: int = 3072


def get_provider(cfg: EmbedConfig) -> EmbeddingProvider:
    if cfg.mode == "dev":
        return LocalSentenceTransformersProvider(model_name=cfg.local_model_name)
    if cfg.mode == "prod":
        return CloudEmbeddingProvider(model_name=cfg.prod_model_name, dim=cfg.prod_dim)
    raise ValueError(f"Unknown mode: {cfg.mode}")


def embed_and_store_patterns(
    qdrant_url: str, patterns: Sequence[Pattern], cfg: EmbedConfig,
    qdrant_api_key: Optional[str] = None,
) -> Tuple[str, str, int]:
    """Returns: (collection_name, embedding_model_name, dim)"""
    provider = get_provider(cfg)
    collection = cfg.qdrant_collection_dev if cfg.mode == "dev" else cfg.qdrant_collection_prod
    qd = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    ensure_qdrant_collection(qd, collection_name=collection, dim=provider.dim)
    texts = [render_pattern_text(p) for p in patterns]
    vectors = provider.embed_texts(texts)
    upsert_patterns_qdrant(
        qd, collection_name=collection, patterns=patterns, vectors=vectors,
        embed_model=provider.model_name, embed_dim=provider.dim,
    )
    return collection, provider.model_name, provider.dim
```

### Operational note

Vector dimension is fixed per Qdrant collection. Use separate collections for dev vs. prod:

- `patterns_dev_384` — local / fast / cheap
- `patterns_prod_3072` — cloud / higher quality

Neo4j remains the same; it stores `pattern_id` and metadata, independent of embedding.

### Full pipeline flow

1. **Mine + aggregate** patterns (corpus) → `Pattern` objects + Neo4j payloads
2. **Store** patterns + instances to Neo4j (structure)
3. **Render** patterns → embed using environment-specific provider
4. **Upsert** vectors + payload to Qdrant `patterns_{dev|prod}`
5. **Runtime** recommender queries the correct Qdrant collection depending on env
