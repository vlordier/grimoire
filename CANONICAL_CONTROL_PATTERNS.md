At the meta-thought / procedural level, logic reduces to a small set of canonical control patterns. Think of them as the instruction set of reasoning, analogous to CPU control flow rather than programming syntax.

Below is a clean, minimal, canonical set, grouped by function. This is what you want your system to recognize, store, and recombine.

1. Branching (decision-making)
1.1 Binary decision (IF / ELSE)

Pattern

Evaluate condition

Choose exactly one path

Meta-use

Feasibility checks

Go / no-go decisions

Constraint satisfaction

Failure mode

Condition ill-defined

Premature decision under ambiguity

1.2 Multi-way decision (SWITCH / CASE)

Pattern

Evaluate discriminator

Select one of N mutually exclusive paths

Meta-use

Strategy selection

Architecture choice

Policy routing

Failure mode

Missing cases

Wrong discriminator variable

1.3 Guarded decision (IF with preconditions)

Pattern

Check safety/validity conditions

Only then allow downstream action

Meta-use

Safety gating

Compliance checks

FSM guards

Failure mode

Guards missing or bypassed

2. Iteration (loops)
2.1 Fixed iteration (FOR loop)

Pattern

Iterate over a known finite set

Meta-use

Enumerating options

Comparing candidates

Exhaustive checks

Failure mode

Wrong iteration space

Combinatorial explosion

2.2 Condition-controlled iteration (WHILE loop)

Pattern

Repeat until condition met

Meta-use

Refinement

Optimization

Debugging

Failure mode

Non-termination

Vague stopping condition

2.3 Observe–update loop (DO–WHILE)

Pattern

Act → observe → update → repeat

Meta-use

Experiments

Model fitting

Hypothesis testing

Failure mode

No learning signal

No convergence criterion

3. State-based control (FSM logic)
3.1 Finite State Machine

Pattern

Explicit states

Allowed transitions only

Meta-use

Multi-step processes

Regulated workflows

Safety-critical reasoning

Failure mode

Hidden state

Invalid transitions

3.2 Hierarchical FSM

Pattern

States composed of sub-states

Meta-use

Complex workflows

Nested procedures

Failure mode

Over-complexity

Poor abstraction boundaries

4. Recursion (self-reference)
4.1 Structural recursion

Pattern

Solve problem by solving smaller instances

Meta-use

Decomposition

Divide-and-conquer

Proofs

Failure mode

No base case

Infinite regress

4.2 Meta-recursion (reasoning about reasoning)

Pattern

Inspect and revise the reasoning process itself

Meta-use

Debugging

Reflection

Strategy correction

Failure mode

Analysis paralysis

Endless self-critique

5. Selection & ranking
5.1 Filter

Pattern

Remove invalid candidates

Meta-use

Constraint enforcement

Feasibility pruning

5.2 Rank / Argmax

Pattern

Score options

Select best

Meta-use

Optimization

Tradeoff analysis

Failure mode

Wrong objective

Uncalibrated scoring

5.3 Top-K shortlist

Pattern

Keep small candidate set

Defer final decision

Meta-use

Decision under uncertainty

Exploration vs exploitation

6. Dependency control
6.1 Sequential dependency

Pattern

Step B depends on output of A

Meta-use

Pipelines

Causal reasoning

6.2 Conditional dependency

Pattern

Dependency exists only if condition holds

Meta-use

Optional steps

Contingency planning

6.3 Parallel branches with join

Pattern

Execute branches independently

Merge results

Meta-use

Comparative analysis

Ensemble reasoning

7. Exception & escape patterns
7.1 Early exit (BREAK / RETURN)

Pattern

Terminate early when condition met

Meta-use

Fast failure

Cost control

7.2 Fallback

Pattern

Primary path fails → secondary path

Meta-use

Robustness

Degraded modes

7.3 Escalation

Pattern

Hand off to higher authority or different system

Meta-use

Institutional constraints

Human-in-the-loop

8. Knowledge update patterns
8.1 Hypothesis → test → update

Pattern

Propose

Test

Revise belief

Meta-use

Scientific reasoning

Debugging

8.2 Bayesian update (generalized)

Pattern

Prior → evidence → posterior

Meta-use

Uncertainty handling

Risk assessment

9. Control of uncertainty
9.1 Clarify-before-act

Pattern

Delay action until ambiguity reduced

Meta-use

High-risk domains

Requirements gathering

9.2 Safe-to-fail experiment

Pattern

Small reversible action

Learn cheaply

Meta-use

Exploration

Prototyping

10. Meta-control (your system’s differentiator)
10.1 Autonomy throttling

Pattern

Adjust allowed actions based on danger

Meta-use

Safety systems

Governance

10.2 Guarded execution

Pattern

Execute only if invariants hold

Meta-use

Prevent catastrophic errors

Canonical compression (the punchline)

All of the above collapse into ~6 fundamental control primitives:

Branch (choose path)

Loop (repeat)

State transition (where am I allowed to go)

Select (filter / rank)

Update belief (learn)

Abort / escalate (stop safely)

Your project’s insight is that reasoning traces are programs written in these primitives, and meta-thoughts are reusable subroutines over them.

If you want next, I can:

collapse these into a formal minimal algebra (useful for learning),

map each pattern to FSM templates,

or show how to auto-detect these patterns from raw text traces.

do all 3:
collapse these into a formal minimal algebra (useful for learning),

map each pattern to FSM templates,

or show how to auto-detect these patterns from raw text traces.
1) Formal minimal algebra for procedural reasoning

Treat a reasoning trace as a program over a small set of typed operators. You want something:

compositional (learnable as motifs),

checkable (guards),

mappable to FSM states.

1.1 Core types

Let:

State σ = structured working memory (goals, constraints, beliefs, artifacts, open questions, danger scores, etc.)

Observation o = any evidence (tool output, user answer, metric, quote)

Action a = any external operation (tool call, deploy, change config)

Decision d = discrete choice among options

Belief b = distribution or score vector over hypotheses/options

Artifact A = goal/constraint/assumption/test/metric/etc.

A trace is a sequence of operators that transform σ.

1.2 Minimal operator set (algebra)

Define these primitives as partial functions (may fail / require preconditions):

ASSERT
ASSERT(φ): σ → σ
Adds a claim/constraint/assumption φ into state (typed, with provenance).

ASK
ASK(q): σ → σ'
Emits a question; updates σ with an open slot q.

OBSERVE
OBSERVE(o): σ → σ
Adds evidence to state, links it to claims/hypotheses.

BRANCH
BRANCH(cond, P_true, P_false): σ → σ
Conditional control flow. cond is evaluable from σ (or from a probe).

SELECT
SELECT(S, score, k): σ → (σ, S')
Filter/rank candidates S using scoring functional; returns top-k S'.

ITERATE
ITERATE(stop, body): σ → σ
General loop. stop(σ) decides termination; body is a program.

UPDATE
UPDATE(b, o): σ → σ
Belief update (can be Bayesian-ish, heuristic, or rule-based). Used for “hypothesis→test→update”.

EXECUTE
EXECUTE(a): σ → σ
Perform an action or tool call; yields observation(s) later via OBSERVE.

GUARD
GUARD(pre): σ ↛ σ
If pre(σ) fails, transition is blocked and emits required subgoals.

HALT / ESCALATE
HALT(reason): σ → σ_final
ESCALATE(to, reason): σ → σ
Stops or hands off.

1.3 Composition rules

Sequencing: (P ; Q)(σ) = Q(P(σ))

Programs are ASTs built from these operators.

Patterns are frequent subtrees/subpaths in this algebra.

1.4 Why this is useful for learning

You can map text → operator sequence (op_t) + arguments.

You can mine frequent operator n-grams/motifs.

You can learn a policy: π(σ) -> next_op constrained by GUARD.

2) Map patterns to FSM templates (your ~10 FSMs)

Here’s a direct mapping from the canonical control patterns to FSM templates (states S0–S9). Each “template” is a reusable micro-FSM you can embed inside the big FSMs.

2.1 Branching templates

Binary IF/ELSE

S6_EVALUATE → S7_DECIDE (choose branch) → S3_PLAN for chosen branch

Guard: if condition depends on missing info → divert to S1_CLARIFY

Switch/Case

Same as above but S7_DECIDE selects among N plans

Add “case coverage” check as a GUARD

Guarded decision

Insert GUARD(preconditions) before S7_DECIDE or S4_EXECUTE

If guard fails → S1_CLARIFY or S5_OBSERVE or S3_PLAN depending on what’s missing

2.2 Iteration templates

FOR (enumerate options)

S3_PLAN (define candidate set) → S4_EXECUTE/S6_EVALUATE for each → S7_DECIDE (aggregate)

Usually inside FSM-3 Design&Decide or FSM-4 Optimize

WHILE (refine until done)

Loop: S2_MODEL → S3_PLAN → S4_EXECUTE → S5_OBSERVE → S6_EVALUATE → (back to S2 or S3)

Stop condition explicit artifact: StopCriterion

DO–WHILE (act–observe–update)

S4_EXECUTE → S5_OBSERVE → S6_EVALUATE → (loop)

Typical inside debug/optimize/adversarial

2.3 FSM / Hierarchical FSM templates

Flat FSM

Exactly your global S0–S9 with allowed transitions table

Hierarchical FSM

Each macro state (e.g., S3_PLAN) can invoke a sub-FSM:

PlanSubFSM: option generation → tradeoff matrix → commit

VerifySubFSM: assumptions → falsifiers → tests → confidence

2.4 Recursion templates

Decomposition recursion

S2_MODEL creates subgoals/artifacts → spawn child traces or subgraphs

Each child runs its own FSM; parent does JOIN in S6_EVALUATE/S7_DECIDE

Meta-recursion (reflect)

Triggered when:

too many revision loops,

contradictions,

repeated guard failures.

Transition: S6_EVALUATE → S2_MODEL with a “process critique” artifact.

2.5 Selection & ranking templates

Filter

S2_MODEL (constraints) → S6_EVALUATE (remove infeasible) → S3_PLAN (on remaining)

Argmax / scoring

S6_EVALUATE (compute scores) → S7_DECIDE (pick) → S8_HARDEN (document)

Top-K shortlist

Same as scoring but decision deferred; output is new candidate set artifact.

2.6 Dependency & parallelism templates

Sequential dependency

Encode as DEPENDS_ON edges; enforce in FSM by only allowing S4_EXECUTE when deps satisfied.

Parallel branches + join

S3_PLAN spawns parallel subplans → run each → S6_EVALUATE join → S7_DECIDE

2.7 Exception / escape templates

Early exit

Any state → S9_CLOSE when success criterion met (explicit StopCriterion)

Fallback

S4_EXECUTE fails → S6_EVALUATE → select fallback option → S4_EXECUTE

Escalation

S6_EVALUATE detects institutional/irreversible flags → ESCALATE artifact → S9_CLOSE or wait

3) Auto-detect these patterns from raw text traces

You want an MVP that works in a day, and a path to “good” later.

3.1 Output you want (per step)

For each step t, infer:

op_type ∈ {ASSERT, ASK, OBSERVE, BRANCH, SELECT, ITERATE, UPDATE, EXECUTE, GUARD, HALT, ESCALATE}

fsm_state ∈ S0..S9

role ∈ StepRole

lightweight links: mentions constraints/metrics/options/hypotheses/etc.

3.2 MVP detector (rules + lightweight classifier)

A) Sentence-level cues (regex/keywords)

ASK: ends with ?, or begins with “what/how/why/can we/should we”

ASSERT/PLAN: “we will”, “plan”, “approach”, “steps:”, “first/then”

OBSERVE: “we see”, “results show”, “logs indicate”, numbers/metrics, tool output blocks

BRANCH: “if”, “else”, “unless”, “otherwise”, “in case”

SELECT: “choose”, “pick”, “rank”, “top-k”, “best option”

ITERATE: “repeat”, “iterate”, “until”, “loop”, “again”, “refine”

UPDATE: “update belief”, “therefore likely”, “increase confidence”, “now think”

GUARD: “only if”, “must”, “required”, “blocked”, “before we”

ESCALATE: “legal/team/board needs”, “sign-off”, “approve”, “escalate”

HALT: “stop”, “cannot proceed”, “done”, “conclusion”

B) Chunk-level motifs
Use a sliding window (k=5–8 steps) and detect operator sequences:

Debug loop: ASSERT(symptom) → BRANCH(hypothesis) → EXECUTE(test) → OBSERVE → UPDATE → (ITERATE)

Clarify: many ASK steps early + missing metrics/constraints

Verify: ASSERT(claim) → ASSERT(assumption) → SELECT(tests) → EXECUTE(test) → OBSERVE → UPDATE(confidence)

This gives you early pattern tagging without ML.

3.3 Better detector (structured extraction + sequence labeling)

Upgrade path:

Step 1: Structured extraction
Extract explicit artifacts from text:

Goal, Metric, Constraint, Option, Hypothesis, Risk, Stakeholder
via (a) regex + (b) small LLM “slot fill” prompts.

Step 2: Sequence tagger
Train a token/step classifier:

Inputs: step text embedding + artifact flags + previous op/state

Outputs: op_type, fsm_state

Even a small linear model on embeddings works surprisingly well.

Step 3: Motif mining
Once steps are tagged:

mine frequent subsequences of (op_type, fsm_state)

mine frequent graph motifs using edges like SUPPORTS/REFUTES/REVISES if you infer them.

3.4 Practical “pattern detection” algorithm

For each trace:

split into steps

tag each step with op_type (rules + classifier)

Build a mini control-flow graph:

sequential NEXT

infer BRANCH edges if a step contains “if/else” and next steps look like alternatives

infer REVISES if text contains “actually / correction / revise”

Detect motifs:

n-gram matching over op_type

subgraph isomorphism for small motifs (optional; start with n-grams)

Emit:

PatternInstance linking step_ids to a Pattern

3.5 What to store for explainability

For every tag/motif:

the evidence (matched phrases / classifier confidence)

the span (which tokens triggered it)
This is essential to debug mis-tags.

If you want the next concrete step

I can provide:

a minimal Pydantic OpTag model + detect_ops(step_text) implementation,

and a mine_motifs(tagged_steps) function that emits Pattern + PatternInstance objects matching your canonical schema.

yes do that
"""
op_detection_and_mining.py (Pydantic v2)

Minimal, shippable MVP:
- Step-level operator detection from raw text (rules + scores + evidence spans)
- Simple FSM-state hinting (light heuristics)
- Motif mining over operator n-grams
- Emits Pattern + PatternInstance objects compatible with your canonical schema

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

# -----------------------------
# Enums (minimal subset)
# -----------------------------

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


# -----------------------------
# Pydantic models
# -----------------------------

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

    # debug-friendly
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

    # store a canonical signature for stable IDs & fast matching
    signature: str


class PatternInstance(BaseModel):
    instance_id: str
    pattern_id: str
    trace_id: str
    step_ids: List[str] = Field(default_factory=list)
    bindings: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------
# Rules (regex) for op detection
# -----------------------------

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

# Role hints (very rough)
_ROLE_HINTS: List[Tuple[StepRole, re.Pattern]] = [
    (StepRole.QUESTION, re.compile(r"\?\s*$")),
    (StepRole.PLAN, re.compile(r"\b(plan|steps?:|approach|we will|roadmap)\b", re.I)),
    (StepRole.DECISION, re.compile(r"\b(decide|decision|choose|pick|we'll go with)\b", re.I)),
    (StepRole.VERIFICATION, re.compile(r"\b(verify|validate|test|falsif|replicat|check)\b", re.I)),
    (StepRole.OBSERVATION, re.compile(r"\b(results show|logs|metric|output|observ(e|ation))\b", re.I)),
    (StepRole.ACTION, re.compile(r"\b(run|execute|deploy|apply|implement)\b", re.I)),
    (StepRole.SUMMARY, re.compile(r"\b(summary|in short|overall)\b", re.I)),
]

# FSM state hints (again: heuristic MVP)
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
    """
    Rule-based multi-label op detection with evidence spans.
    Returns a list of OpTag (op_type + score + evidence).
    """
    t = text or ""
    out: List[OpTag] = []

    for op, rules in _RULES.items():
        evid: List[EvidenceSpan] = []
        score = 0.0
        for name, pat, w in rules:
            for m in pat.finditer(t):
                evid.append(EvidenceSpan(pattern=f"{op.value}:{name}", start=m.start(), end=m.end(), match=m.group(0)))
                score += w
        if evid:
            # soft cap; still leaves headroom for multiple matches
            out.append(OpTag(op_type=op, score=min(score, 1.0), evidence=evid))

    # If nothing matched, return OTHER
    if not out:
        out.append(OpTag(op_type=OpType.OTHER, score=0.2, evidence=[]))

    # Sort by score descending
    out.sort(key=lambda x: x.score, reverse=True)
    return out


def choose_primary_op(op_tags: List[OpTag]) -> OpType:
    """
    Primary op selection heuristic:
    - prefer GUARD/ESCALATE/HALT if present and strong
    - else highest score
    """
    if not op_tags:
        return OpType.OTHER

    # priority overrides
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
        step_id=step_id,
        text=text,
        op_tags=op_tags,
        primary_op=primary,
        role=role,
        fsm_state=state,
        debug={
            "primary_op_reason": "priority_override" if primary in {OpType.GUARD, OpType.ESCALATE, OpType.HALT} else "max_score"
        },
    )


# -----------------------------
# Motif mining (n-gram over ops)
# -----------------------------

@dataclass(frozen=True)
class MotifKey:
    ops: Tuple[OpType, ...]
    states: Tuple[Optional[FSMState], ...]


def motif_signature(ops: Sequence[OpType], states: Sequence[Optional[FSMState]]) -> str:
    return " | ".join(
        f"{op.value}:{(st.value if st else 'NA')}" for op, st in zip(ops, states)
    )


def mine_motifs(
    trace_id: str,
    annotated_steps: Sequence[StepAnnotation],
    n: int = 4,
    min_support: int = 3,
    stride: int = 1,
) -> Tuple[List[Pattern], List[PatternInstance]]:
    """
    Mines frequent operator-state n-grams as FSM_SUBPATH patterns.
    - Works on a single trace (support becomes per-corpus when you aggregate across traces).
    - For corpus mining, call this per trace and aggregate motif counters globally.

    Returns:
      - Patterns (unique in this trace)
      - PatternInstances (each occurrence)
    """
    if n <= 1:
        raise ValueError("n must be >= 2")

    ops = [s.primary_op for s in annotated_steps]
    sts = [s.fsm_state for s in annotated_steps]
    step_ids = [s.step_id for s in annotated_steps]

    motif_positions: Dict[MotifKey, List[int]] = defaultdict(list)

    for i in range(0, len(annotated_steps) - n + 1, stride):
        key = MotifKey(ops=tuple(ops[i:i+n]), states=tuple(sts[i:i+n]))
        motif_positions[key].append(i)

    # Filter by support within this trace (for corpus mining, support threshold applies globally)
    kept = {k: pos for k, pos in motif_positions.items() if len(pos) >= min_support}

    patterns: List[Pattern] = []
    instances: List[PatternInstance] = []

    for key, positions in kept.items():
        sig = motif_signature(key.ops, key.states)
        pid = f"pat_{_hash(sig)}"

        # Build a minimal template (roles/states + generic text)
        template_steps: List[PatternTemplateStep] = []
        for op, st in zip(key.ops, key.states):
            # Map op -> typical role
            role = {
                OpType.ASK: StepRole.QUESTION,
                OpType.EXECUTE: StepRole.ACTION,
                OpType.OBSERVE: StepRole.OBSERVATION,
                OpType.SELECT: StepRole.DECISION,
                OpType.UPDATE: StepRole.CRITIQUE,
                OpType.GUARD: StepRole.VERIFICATION,
                OpType.BRANCH: StepRole.DECISION,
                OpType.ITERATE: StepRole.PLAN,
                OpType.ASSERT: StepRole.OTHER,
                OpType.HALT: StepRole.SUMMARY,
                OpType.ESCALATE: StepRole.DECISION,
                OpType.OTHER: StepRole.OTHER,
            }.get(op, StepRole.OTHER)

            template_steps.append(
                PatternTemplateStep(
                    role=role,
                    fsm_state=st,
                    text_template=f"{op.value} step",
                    slots={},
                )
            )

        pat = Pattern(
            pattern_id=pid,
            type=PatternType.FSM_SUBPATH,
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

        # Instances
        for pos in positions:
            inst_id = f"inst_{_hash(trace_id + pid + str(pos))}"
            inst_steps = step_ids[pos:pos+n]
            instances.append(
                PatternInstance(
                    instance_id=inst_id,
                    pattern_id=pid,
                    trace_id=trace_id,
                    step_ids=inst_steps,
                    bindings={},
                )
            )

    return patterns, instances


# -----------------------------
# Example usage
# -----------------------------

def annotate_trace(trace_id: str, steps: List[Tuple[str, str]]) -> List[StepAnnotation]:
    """
    steps: list[(step_id, text)]
    """
    ann: List[StepAnnotation] = []
    for sid, txt in steps:
        ann.append(annotate_step(step_id=sid, text=txt))
    return ann


if __name__ == "__main__":
    # Tiny demo trace (toy)
    trace_id = "trace_demo"
    raw_steps = [
        ("s0", "We need to make the system scalable and robust for production."),
        ("s1", "What is the target latency and QPS?"),
        ("s2", "If we need <50ms, we should avoid heavy cross-encoders."),
        ("s3", "Let's run a quick benchmark on step-window retrieval."),
        ("s4", "Results show 120 QPS at 30ms average latency."),
        ("s5", "Therefore we can keep a small reranker only for top-20."),
        ("s6", "Repeat until we hit 200 QPS without quality regression."),
    ]

    annotated = annotate_trace(trace_id, raw_steps)
    for a in annotated:
        print(a.step_id, a.primary_op, a.role, a.fsm_state)

    pats, insts = mine_motifs(trace_id, annotated_steps=annotated, n=3, min_support=1)
    print(f"Patterns: {len(pats)} Instances: {len(insts)}")
    for p in pats[:3]:
        print(p.pattern_id, p.signature, p.quality.support)

How to use this in your pipeline (minimal)

During ingestion, after you create Step objects, run annotate_step(step_id, text) and store:

step.properties["op_tags"] (or your own field)

step.properties["primary_op"]

step.role, step.fsm_state (as weak labels)

For mining:

run mine_motifs(trace_id, annotated_steps, n=4, min_support=K) per trace

aggregate across traces by Pattern.signature to get global support and better pattern IDs

Promote patterns:

push Pattern to Neo4j

push pattern embeddings (later) to Qdrant patterns

If you want, next I can show the corpus-level aggregation function that:

merges identical signatures across many traces,

assigns stable pattern_id,

updates PatternQuality.support,

and emits Neo4j upserts + Qdrant payloads.

do that:
If you want, next I can show the corpus-level aggregation function that:

merges identical signatures across many traces,

assigns stable pattern_id,

updates PatternQuality.support,

and emits Neo4j upserts + Qdrant payloads.
"""
corpus_pattern_aggregation.py (Pydantic v2)

Corpus-level motif aggregation:
- Merge identical Pattern.signature across many traces
- Assign stable pattern_id (hash(signature))
- Update PatternQuality.support (global)
- Emit:
  (a) Neo4j upsert payloads (patterns + instances)
  (b) Qdrant payloads for the patterns collection (vectors added later)

Assumptions:
- You already have per-trace StepAnnotation and per-trace mined patterns/instances
  from op_detection_and_mining.py
- You will embed patterns later; this emits payload metadata only.

Requires: pydantic>=2
"""

from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

# Import your models from the prior module
# from op_detection_and_mining import Pattern, PatternInstance, PatternType
# Here we re-declare minimal compatible forms to keep this file standalone.


class PatternType(str):
    FSM_SUBPATH = "fsm_subpath"


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


# -----------------------------
# Stable IDs
# -----------------------------

def stable_pattern_id(signature: str, prefix: str = "pat") -> str:
    h = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def stable_instance_id(trace_id: str, pattern_id: str, start_step_id: str, prefix: str = "inst") -> str:
    seed = f"{trace_id}|{pattern_id}|{start_step_id}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


# -----------------------------
# Aggregation
# -----------------------------

@dataclass
class AggregationStats:
    total_patterns_seen: int = 0
    unique_signatures: int = 0
    total_instances: int = 0


class AggregatedPattern(BaseModel):
    pattern: Pattern
    # list of (trace_id, step_ids, bindings)
    instances: List[PatternInstance] = Field(default_factory=list)


def aggregate_patterns_corpus(
    per_trace_patterns: Iterable[Sequence[Pattern]],
    per_trace_instances: Iterable[Sequence[PatternInstance]],
) -> Tuple[List[AggregatedPattern], AggregationStats]:
    """
    Merge patterns by signature across the corpus.
    - Pattern ID becomes stable hash(signature)
    - Quality.support becomes global instance count
    - Instances are re-keyed to stable IDs and stable pattern_id
    """
    by_sig: Dict[str, AggregatedPattern] = {}
    stats = AggregationStats()

    # Build signature -> prototype Pattern
    for patterns in per_trace_patterns:
        for p in patterns:
            stats.total_patterns_seen += 1
            sig = p.signature
            if sig not in by_sig:
                pid = stable_pattern_id(sig)
                proto = p.model_copy(deep=True)
                proto.pattern_id = pid
                proto.quality.support = 0  # filled after instances aggregated
                by_sig[sig] = AggregatedPattern(pattern=proto, instances=[])

    # Attach instances
    for instances in per_trace_instances:
        for inst in instances:
            stats.total_instances += 1
            # We need signature; we only have inst.pattern_id from per-trace mining.
            # So we rely on joining by matching pattern_id to a pattern signature is not possible here
            # unless caller provides mapping. Best practice: carry signature into instance bindings.
            #
            # MVP: assume inst.bindings["_signature"] is present. If not, you can pass a mapping in.
            sig = inst.bindings.get("_signature")
            if not sig or sig not in by_sig:
                # Skip unknown / unjoinable instances
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

    # Update global support
    for agg in by_sig.values():
        agg.pattern.quality.support = len(agg.instances)

    stats.unique_signatures = len(by_sig)
    return list(by_sig.values()), stats


# -----------------------------
# Emitting Neo4j upserts
# -----------------------------

def to_neo4j_pattern_upserts(aggregated: Sequence[AggregatedPattern]) -> Dict[str, Any]:
    """
    Emit a Neo4j-friendly payload:
    - patterns: list[{pattern_id, props}]
    - pattern_instances: list[{instance_id, step_id, pattern_id, props}]
      (one edge per step -> pattern; simplest representation)
    """
    patterns_payload: List[Dict[str, Any]] = []
    instances_payload: List[Dict[str, Any]] = []

    for agg in aggregated:
        p = agg.pattern
        patterns_payload.append(
            {
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
            }
        )

        # Create INSTANCE_OF edges: Step -> Pattern
        # Keep instance_id on the relationship; attach bindings/step_ids on the first step edge.
        for inst in agg.instances:
            bindings_json = json.dumps(inst.bindings) if inst.bindings else "{}"
            step_ids = inst.step_ids or []
            for j, step_id in enumerate(step_ids):
                props = {
                    "bindings_json": bindings_json if j == 0 else None,
                    "step_ids_json": json.dumps(step_ids) if j == 0 else None,
                }
                # remove nulls
                props = {k: v for k, v in props.items() if v is not None}
                instances_payload.append(
                    {
                        "instance_id": inst.instance_id,
                        "step_id": step_id,
                        "pattern_id": p.pattern_id,
                        "props": props,
                    }
                )

    return {"patterns": patterns_payload, "pattern_instances": instances_payload}


# -----------------------------
# Emitting Qdrant payloads (no vectors here)
# -----------------------------

def to_qdrant_pattern_points_payload(aggregated: Sequence[AggregatedPattern]) -> List[Dict[str, Any]]:
    """
    Emit metadata payloads for the Qdrant 'patterns' collection.
    Vectors should be added separately when you embed the pattern prototype text.
    """
    points: List[Dict[str, Any]] = []

    for agg in aggregated:
        p = agg.pattern
        app = p.applicability
        points.append(
            {
                "id": p.pattern_id,
                "payload": {
                    "pattern_id": p.pattern_id,
                    "type": p.type,
                    "name": p.name,
                    "description": p.description or "",
                    "fsm_id": None,  # if you add FSMId later
                    "allowed_states": app.allowed_states,
                    "domains": [],  # fill if you have
                    "required_tags": [],
                    "forbidden_tags": [],
                    "quality_support": p.quality.support,
                    "quality_success_proxy": None,
                    "miner_version": "miner_v1",
                    "schema_version": "v1",
                    # Optional: store signature for debugging
                    "signature": p.signature,
                    # Optional: store required ops to filter
                    "required_ops": app.required_ops,
                }
            }
        )

    return points


# -----------------------------
# Practical glue: ensure instances carry signature
# -----------------------------

def attach_signature_to_instances(
    patterns: Sequence[Pattern],
    instances: Sequence[PatternInstance],
) -> List[PatternInstance]:
    """
    Ensures each instance.bindings["_signature"] exists so corpus aggregation can join.
    This is the minimal hack that avoids needing an external mapping.
    """
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


# -----------------------------
# Example usage
# -----------------------------

if __name__ == "__main__":
    # Suppose you mined two traces and got patterns/instances per trace.
    # Here we mock minimal objects.

    p1 = Pattern(
        pattern_id="pat_tmp_1",
        type=PatternType.FSM_SUBPATH,
        name="Motif: ASK → BRANCH → EXECUTE",
        description="",
        applicability=PatternApplicability(allowed_states=["S1_clarify", "S3_plan"], required_ops=["ASK", "BRANCH", "EXECUTE"]),
        template=[],
        quality=PatternQuality(support=1),
        signature="ASK:NA | BRANCH:NA | EXECUTE:NA",
    )
    inst1 = PatternInstance(
        instance_id="inst_tmp_1",
        pattern_id="pat_tmp_1",
        trace_id="trace_a",
        step_ids=["a1", "a2", "a3"],
        bindings={},
    )

    p2 = Pattern(
        pattern_id="pat_tmp_2",
        type=PatternType.FSM_SUBPATH,
        name="Motif: ASK → BRANCH → EXECUTE",
        description="",
        applicability=PatternApplicability(allowed_states=["S1_clarify", "S3_plan"], required_ops=["ASK", "BRANCH", "EXECUTE"]),
        template=[],
        quality=PatternQuality(support=1),
        signature="ASK:NA | BRANCH:NA | EXECUTE:NA",  # same signature => should merge
    )
    inst2 = PatternInstance(
        instance_id="inst_tmp_2",
        pattern_id="pat_tmp_2",
        trace_id="trace_b",
        step_ids=["b1", "b2", "b3"],
        bindings={},
    )

    inst1 = attach_signature_to_instances([p1], [inst1])[0]
    inst2 = attach_signature_to_instances([p2], [inst2])[0]

    aggregated, stats = aggregate_patterns_corpus(
        per_trace_patterns=[[p1], [p2]],
        per_trace_instances=[[inst1], [inst2]],
    )

    print(stats)
    neo = to_neo4j_pattern_upserts(aggregated)
    qdr = to_qdrant_pattern_points_payload(aggregated)

    print("Neo4j patterns:", len(neo["patterns"]))
    print("Neo4j instance edges:", len(neo["pattern_instances"]))
    print("Qdrant points:", len(qdr))

How this plugs into your existing modules

For each trace:

annotated = annotate_trace(trace_id, steps)

patterns, instances = mine_motifs(trace_id, annotated, n=4, min_support=1) (or higher in-trace)

instances = attach_signature_to_instances(patterns, instances)

Accumulate across traces:

aggregated, stats = aggregate_patterns_corpus(all_patterns, all_instances)

Write to stores:

Neo4j:

upsert patterns via your UNWIND $patterns ... query

create INSTANCE_OF edges via UNWIND $pattern_instances ...

Qdrant:

upsert payload points into patterns collection (vectors later)

If you want next, I can give you the exact Neo4j driver code (Python) and Qdrant upsert code to apply these payloads end-to-end.

yes
"""
store_writers.py

End-to-end writers:
- Neo4j upsert patterns + create Step-[:INSTANCE_OF]->Pattern edges
- Qdrant upsert pattern points (payload now; vectors optional)

You already have:
- Neo4j DDL + ingestion queries (from earlier)
- Aggregation outputs from corpus_pattern_aggregation.py:
  neo_payload = {"patterns": [...], "pattern_instances": [...]}
  qdrant_points = [{"id": pattern_id, "payload": {...}}, ...]

Dependencies:
  pip install neo4j qdrant-client

Notes:
- Relationship type INSTANCE_OF is fixed here (simple, fast).
- If you want dynamic relationship types, use APOC; we avoid that.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from neo4j import GraphDatabase, Driver
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


# -----------------------------
# Neo4j queries as ready strings
# -----------------------------

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

# Optional: if you also want Trace->Pattern relationships
NEO4J_LINK_TRACE_HAS_PATTERN = """
UNWIND $trace_patterns AS tp
MATCH (t:Trace {trace_id: tp.trace_id})
MATCH (p:Pattern {pattern_id: tp.pattern_id})
MERGE (t)-[r:USES_PATTERN]->(p)
SET r += tp.props
"""


# -----------------------------
# Neo4j writer
# -----------------------------

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
        """
        patterns_payload: list[{pattern_id, props}]
        pattern_instances_payload: list[{instance_id, step_id, pattern_id, props}]
        """
        with self._driver.session(database=self._database) as session:
            # Upsert patterns in batches
            for i in range(0, len(patterns_payload), batch_size):
                batch = patterns_payload[i:i + batch_size]
                session.run(NEO4J_UPSERT_PATTERNS, patterns=batch)

            # Link instances in batches
            for i in range(0, len(pattern_instances_payload), batch_size):
                batch = pattern_instances_payload[i:i + batch_size]
                session.run(NEO4J_LINK_STEP_INSTANCE_OF_PATTERN, pattern_instances=batch)


# -----------------------------
# Qdrant writer
# -----------------------------

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
        """
        points_payload: [{"id": str, "payload": dict}, ...]
        vectors (optional): {pattern_id: [float,...]}
          - If provided, will upsert vectors + payload.
          - If not provided, will upsert payload only (no vector update).

        Note:
          Qdrant requires vectors on insert if the point doesn't already exist.
          So "payload-only upsert" works best after you have inserted vectors once,
          OR if you use a separate "payload-only" collection with no vectors (not typical).
        """
        def mk_point(pid: str, payload: Dict[str, Any]) -> PointStruct:
            if vectors is None:
                # payload-only update requires points exist; Qdrant will error if not.
                # In practice, you should insert vectors at least once.
                return PointStruct(id=pid, vector=[], payload=payload)  # type: ignore[arg-type]
            vec = vectors.get(pid)
            if vec is None:
                raise ValueError(f"Missing vector for pattern_id={pid}")
            return PointStruct(id=pid, vector=vec, payload=payload)

        # Batch upsert
        batch: List[PointStruct] = []
        for p in points_payload:
            pid = str(p["id"])
            payload = dict(p.get("payload") or {})
            batch.append(mk_point(pid, payload))

            if len(batch) >= batch_size:
                self._client.upsert(collection_name=collection, points=batch)
                batch = []

        if batch:
            self._client.upsert(collection_name=collection, points=batch)


# -----------------------------
# Usage example (glue)
# -----------------------------

def write_outputs(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    qdrant_url: str,
    neo_payload: Dict[str, Any],
    qdrant_points: List[Dict[str, Any]],
    qdrant_collection: str = "patterns",
    neo4j_database: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
) -> None:
    # Neo4j
    neo = Neo4jWriter(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)
    try:
        neo.upsert_patterns_and_instances(
            patterns_payload=neo_payload.get("patterns", []),
            pattern_instances_payload=neo_payload.get("pattern_instances", []),
        )
    finally:
        neo.close()

    # Qdrant
    qd = QdrantWriter(url=qdrant_url, api_key=qdrant_api_key)
    # IMPORTANT: vectors=None only works if points already exist.
    # Typically you will embed patterns and provide vectors here.
    qd.upsert_pattern_payloads(collection=qdrant_collection, points_payload=qdrant_points, vectors=None)


if __name__ == "__main__":
    # Example call: you fill neo_payload and qdrant_points from the aggregator.
    example_neo_payload = {"patterns": [], "pattern_instances": []}
    example_qdrant_points: List[Dict[str, Any]] = []

    write_outputs(
        neo4j_uri="neo4j://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        qdrant_url="http://localhost:6333",
        neo_payload=example_neo_payload,
        qdrant_points=example_qdrant_points,
        qdrant_collection="patterns",
    )

Important practical note about Qdrant “payload-only upsert”

Qdrant typically requires vectors when inserting new points. So you have two clean options:

Embed patterns immediately and pass vectors={pattern_id: vector} to upsert_pattern_payloads(...).

Insert “placeholder vectors” once (e.g., zeros of correct dim) and later update vectors.

This keeps the pipeline unblocked if you want to delay embeddings.

If you tell me what embedding model you’ll use (dim + where computed), I can add a small embed_patterns() stub and show the exact end-to-end flow: mine → aggregate → embed → write Neo4j + Qdrant.


If you tell me what embedding model you’ll use (dim + where computed): make this flexible: local small (384) for dev and larger / cloud for prod.
go on
"""
embedding_pipeline_flexible.py

Flexible embedding pipeline:
- Dev: local small model (e.g., sentence-transformers 384-dim)
- Prod: cloud embeddings (any provider) OR bigger local
- Same interface + same downstream writers (Neo4j + Qdrant)

Includes:
- EmbeddingProvider protocol
- LocalSentenceTransformersProvider (384 dim typical)
- CloudEmbeddingProvider stub (you implement)
- Pattern text rendering (Pattern -> canonical string)
- End-to-end: aggregate -> embed -> upsert to Qdrant + Neo4j

Deps:
  pip install pydantic neo4j qdrant-client sentence-transformers numpy
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Reuse your Pattern model shape (simplified here)
class Pattern(BaseModel):
    pattern_id: str
    type: str
    name: str
    description: Optional[str] = None
    signature: str
    applicability_json: Optional[str] = None
    template_json: Optional[str] = None
    quality_support: int = 0


# -----------------------------
# Embedding provider interface
# -----------------------------

class EmbeddingProvider(Protocol):
    @property
    def dim(self) -> int: ...
    @property
    def model_name(self) -> str: ...
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]: ...


# -----------------------------
# Local provider (dev)
# -----------------------------

class LocalSentenceTransformersProvider:
    """
    Typical 384-dim: 'sentence-transformers/all-MiniLM-L6-v2' (384)
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # lazy import
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        # infer dim once
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


# -----------------------------
# Cloud provider (prod) stub
# -----------------------------

class CloudEmbeddingProvider:
    """
    Implement this wrapper around your production embedding service.

    Requirements:
    - return a list of float vectors of constant dim
    - ideally normalized if you use COSINE distance

    Example: call OpenAI / Azure / Voyage / etc.
    """
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


# -----------------------------
# Pattern -> canonical embedding text
# -----------------------------

def render_pattern_text(p: Pattern) -> str:
    """
    Deterministic canonical string; keeps vectors stable across runs.
    """
    parts = [
        f"NAME: {p.name}",
        f"TYPE: {p.type}",
        f"SIGNATURE: {p.signature}",
    ]
    if p.description:
        parts.append(f"DESC: {p.description}")
    if p.applicability_json:
        parts.append(f"APPLICABILITY: {p.applicability_json}")
    if p.template_json:
        parts.append(f"TEMPLATE: {p.template_json}")
    parts.append(f"SUPPORT: {p.quality_support}")
    return "\n".join(parts)


# -----------------------------
# Qdrant helpers
# -----------------------------

def ensure_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    dim: int,
    distance: Distance = Distance.COSINE,
) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        # NOTE: you can't change dim after creation; ensure your dev/prod use different collections
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=distance),
    )


def make_qdrant_pattern_payload(p: Pattern, embed_model: str, embed_dim: int) -> Dict[str, Any]:
    return {
        "pattern_id": p.pattern_id,
        "type": p.type,
        "name": p.name,
        "description": p.description or "",
        "signature": p.signature,
        "quality_support": p.quality_support,
        "embedding_model": embed_model,
        "embedding_dim": embed_dim,
        "schema_version": "v1",
    }


def upsert_patterns_qdrant(
    client: QdrantClient,
    collection_name: str,
    patterns: Sequence[Pattern],
    vectors: Sequence[Sequence[float]],
    embed_model: str,
    embed_dim: int,
    batch_size: int = 256,
) -> None:
    assert len(patterns) == len(vectors)

    points: List[PointStruct] = []
    for p, v in zip(patterns, vectors):
        payload = make_qdrant_pattern_payload(p, embed_model=embed_model, embed_dim=embed_dim)
        points.append(PointStruct(id=p.pattern_id, vector=list(v), payload=payload))
        if len(points) >= batch_size:
            client.upsert(collection_name=collection_name, points=points)
            points = []
    if points:
        client.upsert(collection_name=collection_name, points=points)


# -----------------------------
# End-to-end: embed + upsert
# -----------------------------

@dataclass
class EmbedConfig:
    mode: str  # "dev" | "prod"
    # Use different collections per mode because dims differ.
    qdrant_collection_dev: str = "patterns_dev_384"
    qdrant_collection_prod: str = "patterns_prod"
    # Local dev model
    local_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Prod model metadata (for CloudEmbeddingProvider)
    prod_model_name: str = "your-prod-embedding-model"
    prod_dim: int = 3072


def get_provider(cfg: EmbedConfig) -> EmbeddingProvider:
    if cfg.mode == "dev":
        return LocalSentenceTransformersProvider(model_name=cfg.local_model_name)
    if cfg.mode == "prod":
        return CloudEmbeddingProvider(model_name=cfg.prod_model_name, dim=cfg.prod_dim)
    raise ValueError(f"Unknown mode: {cfg.mode}")


def embed_and_store_patterns(
    qdrant_url: str,
    patterns: Sequence[Pattern],
    cfg: EmbedConfig,
    qdrant_api_key: Optional[str] = None,
) -> Tuple[str, str, int]:
    """
    Returns: (collection_name, embedding_model_name, dim)
    """
    provider = get_provider(cfg)
    collection = cfg.qdrant_collection_dev if cfg.mode == "dev" else cfg.qdrant_collection_prod

    qd = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    ensure_qdrant_collection(qd, collection_name=collection, dim=provider.dim, distance=Distance.COSINE)

    texts = [render_pattern_text(p) for p in patterns]
    vectors = provider.embed_texts(texts)
    upsert_patterns_qdrant(
        qd,
        collection_name=collection,
        patterns=patterns,
        vectors=vectors,
        embed_model=provider.model_name,
        embed_dim=provider.dim,
    )
    return collection, provider.model_name, provider.dim


# -----------------------------
# Practical integration note
# -----------------------------

"""
Key operational detail: dims differ, so do NOT reuse the same Qdrant collection for dev vs prod.

Recommended:
- patterns_dev_384   (local / fast / cheap)
- patterns_prod_3072 (cloud / higher quality)

At runtime, your retrieval layer chooses which collection to query based on environment.
Neo4j remains the same; it stores pattern_id and metadata, independent of embedding.
"""

if __name__ == "__main__":
    # Demo patterns (usually come from your aggregator)
    patterns = [
        Pattern(
            pattern_id="pat_aaaaaaaaaaaaaaaa",
            type="fsm_subpath",
            name="Motif: ASK→BRANCH→EXECUTE→OBSERVE",
            description="Common clarifying-then-test pattern",
            signature="ASK:NA | BRANCH:NA | EXECUTE:NA | OBSERVE:NA",
            applicability_json=json.dumps({"allowed_states": ["S1_clarify", "S3_plan"]}),
            template_json=json.dumps([]),
            quality_support=123,
        )
    ]

    cfg = EmbedConfig(mode="dev")
    collection, model_name, dim = embed_and_store_patterns(
        qdrant_url="http://localhost:6333",
        patterns=patterns,
        cfg=cfg,
    )
    print("Stored to:", collection, model_name, dim)

How to wire this into your full pipeline

Mine + aggregate patterns (corpus) → you already have Pattern objects + Neo4j payloads

Store patterns + instances to Neo4j (structure)

Render patterns → embed using environment-specific provider

Upsert vectors + payload to Qdrant patterns_{dev|prod}

Runtime recommender queries the correct Qdrant collection depending on env

One critical rule

Because vector dimension is fixed per Qdrant collection, you must keep separate collections for dev vs prod (or separate Qdrant instances).