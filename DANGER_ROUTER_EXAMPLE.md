# Python example for the "Danger Router"


```python
"""
danger_router_pydantic.py

Compact reference skeleton (Pydantic):
- Regex + probe-based danger classifier
- Guards integrated into FSM transition checks
- Minimal unit tests (pytest)

Requires: pydantic>=2
Optional: pytest for tests

Design notes:
- ProbeClient is an interface you plug into an LLM provider.
- Scoring is transparent + easy to calibrate later.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


# -----------------------------
# Enums
# -----------------------------

class DangerType(str, Enum):
    AMBIGUITY = "ambiguity"
    ADVERSARIAL = "adversarial"
    IRREVERSIBILITY = "irreversibility"
    INSTITUTIONAL = "institutional"


class Action(str, Enum):
    EXECUTE = "EXECUTE"
    DECIDE = "DECIDE"
    CLOSE = "CLOSE"


# -----------------------------
# Pydantic models
# -----------------------------

class ProbeResult(BaseModel):
    probe_id: str
    answer: str  # "yes" | "no"
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("answer")
    @classmethod
    def _answer_yes_no(cls, v: str) -> str:
        vv = v.strip().lower()
        if vv not in {"yes", "no"}:
            raise ValueError("answer must be 'yes' or 'no'")
        return vv


class DangerEvidence(BaseModel):
    regex_hits: Dict[DangerType, List[str]] = Field(default_factory=dict)
    flags: Dict[str, Any] = Field(default_factory=dict)
    probes: List[ProbeResult] = Field(default_factory=list)


class DangerScores(BaseModel):
    scores: Dict[DangerType, float]
    evidence: DangerEvidence = Field(default_factory=DangerEvidence)

    @model_validator(mode="after")
    def _validate_scores(self) -> "DangerScores":
        # Ensure all four keys exist, clip to [0,1]
        for dt in DangerType:
            if dt not in self.scores:
                self.scores[dt] = 0.0
            self.scores[dt] = clip01(float(self.scores[dt]))
        return self

    def score(self, t: DangerType) -> float:
        return float(self.scores.get(t, 0.0))

    def status(self, t: DangerType) -> str:
        s = self.score(t)
        if s >= 0.80:
            return "critical"
        if s >= 0.60:
            return "dominant"
        if s >= 0.30:
            return "present"
        return "absent"


class RoutingDecision(BaseModel):
    danger: DangerScores
    routing_actions: List[str]
    autonomy_level: str  # "VERY_LOW" | "LOW" | "MEDIUM" | "HIGH"
    blocked_actions: List[Action]


class FSMContext(BaseModel):
    danger: DangerScores

    # checklist flags set as conversation proceeds
    definition_complete: bool = False
    verification_passed: bool = False
    monitoring_plan_exists: bool = False
    stakeholder_map_exists: bool = False

    # whether the next action is irreversible (caller sets per situation)
    next_is_irreversible: bool = False


# -----------------------------
# Probes interface
# -----------------------------

class ProbeClient(Protocol):
    def run_probes(self, text: str, probe_specs: List[Dict[str, str]]) -> List[ProbeResult]:
        """
        Implement with your LLM provider.
        Must return valid ProbeResult list (Pydantic models).
        """
        ...


# -----------------------------
# Regex rules
# -----------------------------

METRIC_TOKENS = re.compile(
    r"\b(ms|s|sec|seconds|latency|throughput|qps|rps|fps|accuracy|f1|precision|recall|auc|"
    r"bleu|rouge|wer|cer|cost|€|\$|budget|memory|gb|mb|cpu|gpu|watt|wh|kwh|sla|slo)\b",
    re.IGNORECASE,
)

RULES: Dict[DangerType, List[Tuple[str, re.Pattern]]] = {
    DangerType.AMBIGUITY: [
        ("vague_verb", re.compile(r"\b(improve|better|enhance|optimi[sz]e|increase|reduce|make|handle|support|enable|ensure)\b", re.I)),
        ("vague_adj", re.compile(r"\b(scalable|robust|reliable|secure|safe|fast|efficient|user[- ]?friendly|production[- ]?ready)\b", re.I)),
        ("missing_object", re.compile(r"\b(make|improve|optimi[sz]e|fix)\s+(it|this|that)\b", re.I)),
    ],
    DangerType.ADVERSARIAL: [
        ("adversarial_terms", re.compile(r"\b(adversar(y|ial)|attack|bypass|evade|abuse|fraud|spam|bot(s)?|cheat|exploit|poison(ing)?|prompt injection|jailbreak|ddos|phish(ing)?|malware|red team)\b", re.I)),
        ("tands", re.compile(r"\b(content moderation|trust and safety|t&s)\b", re.I)),
        ("incentives", re.compile(r"\b(incentive|game(d|ing)?|arms race|cat[- ]?and[- ]?mouse|adaptive|strateg(y|ic))\b", re.I)),
    ],
    DangerType.IRREVERSIBILITY: [
        ("high_stakes_domain", re.compile(r"\b(medical|patient|clinical|diagnos(is|e)|treatment|drug|dose|legal|court|lawsuit|compliance|regulator(y)?|safety[- ]critical|aviation|automotive|nuclear|financial advice|credit decision)\b", re.I)),
        ("no_rollback", re.compile(r"\b(irrevocable|irreversible|cannot undo|no rollback|one[- ]?way door|point of no return|permanent)\b", re.I)),
        ("harm_terms", re.compile(r"\b(life|death|harm|injur(y|ies)|liability|fine(s)?|penalt(y|ies)|prison|reputation(al)? damage)\b", re.I)),
    ],
    DangerType.INSTITUTIONAL: [
        ("stakeholders", re.compile(r"\b(board|committee|leadership|exec(s)?|legal team|procurement|union|works council|regulator|auditor|compliance|risk team|security team|stakeholder(s)?)\b", re.I)),
        ("politics", re.compile(r"\b(politic(s|al)|optics|narrative|buy[- ]?in|alignment|approval|sign[- ]?off|veto|governance|bureaucrac(y|ies)|public sector)\b", re.I)),
        ("blocked", re.compile(r"\b(they (won't|will not|refuse)|not allowed|forbidden|blocked|cannot get approval)\b", re.I)),
    ],
}


# -----------------------------
# Probes
# -----------------------------

PROBES: List[Dict[str, str]] = [
    # Ambiguity
    {"probe_id": "amb_success_defined", "question": "Is the success criterion (metric + target + horizon) explicitly defined? Answer yes/no."},
    {"probe_id": "amb_scope_defined", "question": "Is scope clearly defined (in/out)? Answer yes/no."},
    # Adversarial
    {"probe_id": "adv_adaptive_agent", "question": "Is there an agent that may try to evade, exploit, or adapt to the solution? Answer yes/no."},
    # Irreversibility
    {"probe_id": "irr_hard_to_rollback", "question": "Would an error cause serious harm, legal exposure, or be hard to roll back? Answer yes/no."},
    # Institutional
    {"probe_id": "inst_power_blocks", "question": "Are approvals, politics, optics, or governance likely to be the binding constraint? Answer yes/no."},
]


def default_probe_specs() -> List[Dict[str, str]]:
    return list(PROBES)


class ProbeCache(BaseModel):
    by_hash: Dict[str, List[ProbeResult]] = Field(default_factory=dict)

    def get(self, text: str) -> Optional[List[ProbeResult]]:
        return self.by_hash.get(hash_text(text))

    def put(self, text: str, results: List[ProbeResult]) -> None:
        self.by_hash[hash_text(text)] = results


# -----------------------------
# Core logic
# -----------------------------

def clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_regex_features(text: str) -> Tuple[Dict[DangerType, List[str]], Dict[str, Any]]:
    t = text or ""
    hits: Dict[DangerType, List[str]] = {dt: [] for dt in DangerType}

    for dt, rules in RULES.items():
        for name, pat in rules:
            if pat.search(t):
                hits[dt].append(name)

    has_metric = bool(METRIC_TOKENS.search(t))
    fast = bool(re.search(r"\b(fast|low latency|latency)\b", t, re.I))
    cheap = bool(re.search(r"\b(cheap|low cost|budget)\b", t, re.I))
    safe = bool(re.search(r"\b(safe|secure|reliable|compliance)\b", t, re.I))
    conflict = (int(fast) + int(cheap) + int(safe)) >= 2

    flags = {
        "has_metric_tokens": has_metric,
        "conflicting_constraints": bool(conflict),
        "fast": fast,
        "cheap": cheap,
        "safe": safe,
    }
    return hits, flags


def probe_yes(probes: List[ProbeResult], probe_id: str) -> float:
    for p in probes:
        if p.probe_id == probe_id:
            return p.confidence if p.answer == "yes" else 0.0
    return 0.0


def score_dangers(regex_hits: Dict[DangerType, List[str]], flags: Dict[str, Any], probes: List[ProbeResult]) -> Dict[DangerType, float]:
    # Ambiguity
    amb_hits = min(len(regex_hits[DangerType.AMBIGUITY]), 5)
    amb_absence = 1.0 if (not flags.get("has_metric_tokens") and amb_hits > 0) else 0.0
    amb_conflict = 1.0 if flags.get("conflicting_constraints") else 0.0
    amb_probe_no_success = 1.0 - probe_yes(probes, "amb_success_defined")
    amb_probe_no_scope = 1.0 - probe_yes(probes, "amb_scope_defined")

    ambiguity = clip01(
        0.18 * amb_hits
        + 0.25 * amb_absence
        + 0.12 * amb_conflict
        + 0.22 * amb_probe_no_success
        + 0.23 * amb_probe_no_scope
    )

    # Adversarial
    adv_hits = min(len(regex_hits[DangerType.ADVERSARIAL]), 5)
    adversarial = clip01(0.18 * adv_hits + 0.50 * probe_yes(probes, "adv_adaptive_agent"))

    # Irreversibility
    irr_hits = min(len(regex_hits[DangerType.IRREVERSIBILITY]), 5)
    irreversibility = clip01(0.18 * irr_hits + 0.55 * probe_yes(probes, "irr_hard_to_rollback"))

    # Institutional
    inst_hits = min(len(regex_hits[DangerType.INSTITUTIONAL]), 5)
    institutional = clip01(0.18 * inst_hits + 0.55 * probe_yes(probes, "inst_power_blocks"))

    return {
        DangerType.AMBIGUITY: ambiguity,
        DangerType.ADVERSARIAL: adversarial,
        DangerType.IRREVERSIBILITY: irreversibility,
        DangerType.INSTITUTIONAL: institutional,
    }


def danger_classifier(
    text: str,
    probe_client: Optional[ProbeClient] = None,
    probe_cache: Optional[ProbeCache] = None,
    use_probes: bool = True,
) -> DangerScores:
    regex_hits, flags = extract_regex_features(text)
    probes: List[ProbeResult] = []

    if use_probes and probe_client is not None:
        if probe_cache is not None:
            cached = probe_cache.get(text)
            if cached is not None:
                probes = cached
            else:
                probes = probe_client.run_probes(text, default_probe_specs())
                probe_cache.put(text, probes)
        else:
            probes = probe_client.run_probes(text, default_probe_specs())

    scores = score_dangers(regex_hits, flags, probes)
    evidence = DangerEvidence(regex_hits=regex_hits, flags=flags, probes=probes)
    return DangerScores(scores=scores, evidence=evidence)


# -----------------------------
# Routing + guards
# -----------------------------

def routing_decision(danger: DangerScores) -> RoutingDecision:
    actions: List[str] = []
    blocked: List[Action] = []

    amb = danger.score(DangerType.AMBIGUITY)
    adv = danger.score(DangerType.ADVERSARIAL)
    irr = danger.score(DangerType.IRREVERSIBILITY)
    inst = danger.score(DangerType.INSTITUTIONAL)

    if amb >= 0.60:
        actions.append("FORCE_FSM_CLARIFY")
        blocked.extend([Action.EXECUTE, Action.DECIDE])

    if irr >= 0.60:
        actions.append("ADD_IRREVERSIBLE_GATES")
        blocked.extend([Action.DECIDE, Action.EXECUTE])

    if adv >= 0.60:
        actions.append("REQUIRE_THREAT_MODEL_AND_MONITORING")

    if inst >= 0.60:
        actions.append("REQUIRE_STAKEHOLDER_MAP")

    if irr >= 0.60 and amb >= 0.60:
        autonomy = "VERY_LOW"
    elif irr >= 0.60 or amb >= 0.60:
        autonomy = "LOW"
    elif adv >= 0.60 or inst >= 0.60:
        autonomy = "MEDIUM"
    else:
        autonomy = "HIGH"

    # de-dup preserving order
    actions = list(dict.fromkeys(actions))
    blocked = list(dict.fromkeys(blocked))

    return RoutingDecision(
        danger=danger,
        routing_actions=actions,
        autonomy_level=autonomy,
        blocked_actions=blocked,
    )


def guard_no_execute_while_ambiguous(ctx: FSMContext) -> Tuple[bool, str]:
    if ctx.danger.score(DangerType.AMBIGUITY) >= 0.60 and not ctx.definition_complete:
        return False, "Blocked: ambiguity dominant and definition not complete (force Clarify & Frame)."
    return True, ""


def guard_no_irreversible_without_verification(ctx: FSMContext) -> Tuple[bool, str]:
    if ctx.next_is_irreversible and ctx.danger.score(DangerType.IRREVERSIBILITY) >= 0.60 and not ctx.verification_passed:
        return False, "Blocked: irreversibility dominant and verification gate not passed."
    return True, ""


def guard_adversarial_requires_monitoring_to_close(ctx: FSMContext) -> Tuple[bool, str]:
    if ctx.danger.score(DangerType.ADVERSARIAL) >= 0.60 and not ctx.monitoring_plan_exists:
        return False, "Blocked: adversarial dominant and no monitoring/iteration plan exists."
    return True, ""


def guard_institutional_requires_stakeholder_map_for_decide(ctx: FSMContext) -> Tuple[bool, str]:
    if ctx.danger.score(DangerType.INSTITUTIONAL) >= 0.60 and not ctx.stakeholder_map_exists:
        return False, "Blocked: institutional dominant and stakeholder/veto map missing."
    return True, ""


def can_transition(ctx: FSMContext, action: Action) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    if action == Action.EXECUTE:
        ok, r = guard_no_execute_while_ambiguous(ctx)
        if not ok:
            reasons.append(r)
        ok, r = guard_no_irreversible_without_verification(ctx)
        if not ok:
            reasons.append(r)

    if action == Action.DECIDE:
        ok, r = guard_institutional_requires_stakeholder_map_for_decide(ctx)
        if not ok:
            reasons.append(r)
        ok, r = guard_no_irreversible_without_verification(ctx)
        if not ok:
            reasons.append(r)

    if action == Action.CLOSE:
        ok, r = guard_adversarial_requires_monitoring_to_close(ctx)
        if not ok:
            reasons.append(r)

    return (len(reasons) == 0), reasons


# -----------------------------
# Tests (pytest)
# -----------------------------
# Save as test_danger_router_pydantic.py and run: pytest -q

def _fake_probes_yes(yes_ids: List[str]) -> List[ProbeResult]:
    out: List[ProbeResult] = []
    for ps in default_probe_specs():
        pid = ps["probe_id"]
        if pid in yes_ids:
            out.append(ProbeResult(probe_id=pid, answer="yes", confidence=0.9))
        else:
            out.append(ProbeResult(probe_id=pid, answer="no", confidence=0.9))
    return out


def test_ambiguity_detects_vague_no_metrics():
    text = "Make it scalable and robust for production."
    hits, flags = extract_regex_features(text)
    probes = _fake_probes_yes(yes_ids=[])  # all "no"
    scores = score_dangers(hits, flags, probes)
    assert scores[DangerType.AMBIGUITY] >= 0.60


def test_adversarial_detects_fraud():
    text = "We need to prevent fraud and attackers bypassing checks."
    hits, flags = extract_regex_features(text)
    probes = _fake_probes_yes(yes_ids=["adv_adaptive_agent"])
    scores = score_dangers(hits, flags, probes)
    assert scores[DangerType.ADVERSARIAL] >= 0.60


def test_irreversibility_blocks_decide_without_verification():
    danger = DangerScores(
        scores={
            DangerType.AMBIGUITY: 0.1,
            DangerType.ADVERSARIAL: 0.1,
            DangerType.IRREVERSIBILITY: 0.8,
            DangerType.INSTITUTIONAL: 0.1,
        }
    )
    ctx = FSMContext(danger=danger, verification_passed=False, next_is_irreversible=True)
    ok, reasons = can_transition(ctx, Action.DECIDE)
    assert not ok
    assert any("verification gate" in r.lower() for r in reasons)


def test_institutional_requires_stakeholder_map():
    danger = DangerScores(
        scores={
            DangerType.AMBIGUITY: 0.1,
            DangerType.ADVERSARIAL: 0.1,
            DangerType.IRREVERSIBILITY: 0.1,
            DangerType.INSTITUTIONAL: 0.7,
        }
    )
    ctx = FSMContext(danger=danger, stakeholder_map_exists=False)
    ok, reasons = can_transition(ctx, Action.DECIDE)
    assert not ok
    assert any("stakeholder" in r.lower() for r in reasons)


def test_routing_decision_forces_clarify_on_ambiguity():
    danger = DangerScores(
        scores={
            DangerType.AMBIGUITY: 0.7,
            DangerType.ADVERSARIAL: 0.1,
            DangerType.IRREVERSIBILITY: 0.1,
            DangerType.INSTITUTIONAL: 0.1,
        }
    )
    rd = routing_decision(danger)
    assert "FORCE_FSM_CLARIFY" in rd.routing_actions
    assert Action.EXECUTE in rd.blocked_actions
    assert rd.autonomy_level in ("LOW", "VERY_LOW")
```
