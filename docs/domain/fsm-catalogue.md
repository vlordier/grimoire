# FSM Catalogue

> 10 universal finite-state machines covering the [15 problem archetypes](problem-archetypes.md). Archetype 12 (Ambiguity Resolution) maps to FSM-1, archetype 13 (Adversarial/Strategic) maps to FSM-10, and archetypes 14–15 are handled as global modifiers rather than separate FSMs. Archetypes 4 (Explanation/Sense-making) and 11 (Meta-process Design) are not yet mapped to dedicated FSMs — see [Known gaps](#known-gaps) below.
>
> **See also:** [Problem Archetypes](problem-archetypes.md) · [Danger Classification](danger-classification.md) · [Control Pattern Taxonomy](control-pattern-taxonomy.md) · [Canonical Schemas](../reference/canonical-schemas.md)

---

## Common State Vocabulary

All FSMs share this state set for uniform implementation:

| State | Name | Purpose |
|-------|------|---------|
| **S0** | Intake | Receive and register the problem |
| **S1** | Clarify | Resolve ambiguity, gather missing info |
| **S2** | Model | Build mental/causal/structural model |
| **S3** | Plan | Generate options, strategies, experiments |
| **S4** | Execute | Perform actions, tool calls, implementations |
| **S5** | Observe | Collect evidence, results, metrics |
| **S6** | Evaluate | Compare, score, assess against criteria |
| **S7** | Decide | Choose between options, commit |
| **S8** | Harden | Add monitoring, guardrails, documentation |
| **S9** | Close | Finalize, confirm, record outcome |

Implementation options:
* A top-level FSM per session/trace
* Nested sub-FSMs per chunk (windows of steps)

---

## FSM-1: Clarify & Frame (Problem Definition)

**Covers:** Ambiguity Resolution (12) + early stage of almost everything

**States:** S0 → S1 → S2 → S7 → S9

**Transitions**
* S0→S1 if goal/constraints are vague or conflicting
* S1→S2 once you have: objective, scope, success metric, constraints, stakeholders
* S2→S7 when you can choose: archetype + approach + next questions/plan
* S7→S9 when alignment is confirmed (or "insufficient info, stop")

**Key outputs (graph artifacts)**
* `Goal{definition, metric, horizon}`
* `Scope{in, out}`
* `Constraints{hard, soft}`
* `Assumptions`
* `OpenQuestions`
* `ArchetypeLabel` (+ confidence)

**Exit criteria:** "We all agree what success means" OR "cannot proceed without X"

---

## FSM-2: Diagnose & Fix (Debug Loop)

**Covers:** Diagnosis/Debugging (1)

**States:** S0 → S2 → S3 → S4 → S5 → S6 → (S3 or S8) → S9

**Transitions**
* S0→S2 always (build causal model of failure)
* S2→S3 create ranked hypotheses
* S3→S4 run discriminating tests / reproduce / bisect
* S4→S5 capture observations
* S5→S6 update belief over hypotheses
* S6→S3 if ambiguity remains
* S6→S8 when root cause confirmed and fix chosen
* S8→S9 after verification + guardrails

**Graph signature:** Repeating cycle: `Hypothesis → Test → Observation → Update`
Node types: `Symptom`, `Hypothesis`, `Test`, `Evidence`, `RootCause`, `Fix`, `RegressionTest`

**Exit criteria:** Root cause confirmed + fix verified + monitor/guardrail added

---

## FSM-3: Design & Decide (Constraint-Satisfying Design Funnel)

**Covers:** Design under constraints (2) + many decisions (5)

**States:** S0 → S1 → S2 → S3 → S7 → S8 → S9

**Transitions**
* S1→S2 produce requirements model + constraints map
* S2→S3 generate options, tradeoff criteria, evaluation plan
* S3→S7 after evaluating 2–5 viable options
* S7→S8 once a design is selected (interfaces, ADRs, rollout)
* S8→S9 once deliverables and owners exist

**Graph artifacts:** `Option` nodes with `Pros/Cons`, `Cost`, `Risk`; `Constraint` nodes + `Violates` edges; `Decision` node with `Rationale`

**Exit criteria:** Decision recorded + implementation plan exists

---

## FSM-4: Optimize (Experiment Loop)

**Covers:** Optimization (3)

**States:** S0 → S2 → S3 → S4 → S5 → S6 → (S3 or S9)

**Transitions**
* S2 defines metric model + levers
* S3 picks highest ROI experiment
* S6→S3 if more headroom
* S6→S9 if diminishing returns or risk threshold reached

**Graph artifacts:** `Metric`, `Baseline`, `Intervention`, `Result`, `Regression`, `Decision(keep/revert)`

**Exit criteria:** Metric target met OR marginal gain too small OR risk too high

---

## FSM-5: Verify (Claim Testing / Audit)

**Covers:** Validation/Verification (9) + part of one-way-door (15)

**States:** S0 → S1 → S2 → S3 → S4 → S5 → S6 → S9

**Transitions**
* S1 pin down exact claim + acceptance threshold
* S2 enumerate assumptions + falsifiers
* S3 design independent tests/replications
* S6 concludes with calibrated confidence (not just yes/no)

**Graph artifacts:** `Claim`, `Assumption`, `Falsifier`, `TestPlan`, `Replication`, `Confidence`

**Exit criteria:** Confidence statement + evidence trail + known limits

---

## FSM-6: Transform (Translation with Invariants)

**Covers:** Translation/Transformation (6)

**States:** S0 → S1 → S2 → S3 → S4 → S6 → (S4 or S9)

**Transitions**
* S1 define target format + invariants + oracle tests
* S2 map source→target constructs
* S4 do incremental transforms
* S6 validate equivalence continuously; loop until done

**Graph artifacts:** `Invariant`, `OracleTest`, `Mapping`, `MigrationStep`, `EquivalenceCheck`

**Exit criteria:** Target produced + invariants satisfied + rollback path (if relevant)

---

## FSM-7: Operate & Harden (Productionization)

**Covers:** Operationalization/Productionization (10) + part of design (2)

**States:** S0 → S2 → S3 → S4 → S5 → S6 → S8 → S9

**Transitions**
* S2 identify failure modes + SLO/SLA
* S3 define monitoring/alerting/runbooks/rollout
* S4 implement reliability features + deploy staged
* S8 finalize ownership, docs, rollback, on-call readiness

**Graph artifacts:** `SLO`, `FailureMode`, `Monitor`, `Alert`, `Runbook`, `RolloutStep`, `Owner`

**Exit criteria:** Production readiness criteria satisfied

---

## FSM-8: Postmortem & Prevent (Backwards Causality)

**Covers:** Failure analysis/post-mortem (8)

**States:** S0 → S2 → S5 → S6 → S8 → S9

**Transitions**
* S2 builds timeline/causal model (backwards)
* S5 collects evidence
* S6 separates root causes vs contributing factors
* S8 creates preventive/detective actions + owners

**Graph artifacts:** `TimelineEvent`, `Trigger`, `Impact`, `RootCause`, `ContribFactor`, `ActionItem`

**Exit criteria:** Action items with owners + follow-up date; learning recorded as pattern

---

## FSM-9: Resolve Conflicts (Constraint Arbitration)

**Covers:** Constraint conflict resolution (7) + institutional/one-way-door interactions

**States:** S0 → S1 → S2 → S3 → S7 → S9

**Transitions**
* S1: enumerate constraints + authority levels
* S2: prove infeasibility / conflict
* S3: generate compromise packages + scope/time adjustments
* S7: escalate to authority when needed; record decision

**Graph artifacts:** `Constraint`, `Authority`, `Conflict`, `CompromiseOption`, `Escalation`, `Decision`

**Exit criteria:** Tradeoff accepted by authority + residual risk documented

---

## FSM-10: Adversarial Adaptation (Threat-Defense Loop)

**Covers:** Adversarial/strategic problems (13)

**States:** S0 → S2 → S3 → S4 → S5 → S6 → (S3 or S8) → S9

**Transitions**
* S2 define adversary model + incentives + capabilities
* S3 design defense-in-depth + detection/response
* S6 update model based on observed adaptation
* S8 harden monitoring + iteration cadence

**Graph artifacts:** `Adversary`, `Attack`, `Defense`, `Detection`, `Response`, `GameLoop`

**Exit criteria:** Robust baseline defense + monitoring + iteration plan (never "done forever")

---

## Global Modifiers

Archetypes 14 (One-way Door Gating) and 15 (Institutional Navigation) are **not separate FSMs** — they are **modifiers** that wrap any FSM with additional states/edges. (Archetypes 12 and 13 are covered by FSM-1 and FSM-10 respectively.)

### Modifier A: Institutional Navigation

Add states/edges to any FSM:
* `StakeholderMap`, `VetoPoint`, `Coalition`, `CommsPlan`

Common insertion: between S3 Plan and S7 Decide (and again before S8 Harden)

### Modifier B: One-way Door Gating

Add gates to any FSM:
* `IndependentReview`, `Redundancy`, `Pilot`, `Signoff`

Common insertion: before any irreversible transition (usually before S4 Execute or S7 Decide)

This keeps us at 10 FSMs while still covering the remaining archetypes.

---

## Known Gaps

Two archetypes do not yet have dedicated FSM mappings:

| Archetype | Current coverage | Notes |
|-----------|-----------------|-------|
| **4 — Explanation / Sense-making** | Partially covered by FSM-3 (Design & Decide) when the goal is explanatory | May warrant a dedicated "Explain & Teach" FSM if usage patterns diverge from design workflows |
| **11 — Meta-process Design** | Partially covered by FSM-7 (Operate & Harden) for process operationalization | May warrant a dedicated "Process Design" FSM; currently the gap is small because meta-process design typically decomposes into design + operate sub-problems |

---

## Transition Guards

> Migrated from the danger classification design. These guards enforce safety constraints on FSM transitions based on danger scores. For the scoring model, see [Danger Classification](danger-classification.md).

### DangerGate (pre-routing step)

Before committing to any main FSM, on every new problem statement:

1. Run `danger_classifier(text)` → 4 scores
2. Set `autonomy_level`
3. Set `required_modifiers`
4. If ambiguity ≥ 0.60 → force FSM-1 (Clarify & Frame)
5. Else choose initial base FSM via normal router
6. Apply modifiers (adversarial, irreversible, institutional)

### Guard G1: No execution while ambiguous

**Blocks:** S3→S4, S2→S4

**Condition:** `ambiguity >= 0.60 AND definition_complete == false`

`definition_complete` becomes true when:
* metric/target/horizon defined OR explicitly "no metric, exploratory"
* scope in/out defined
* constraints list exists

### Guard G2: No irreversible decisions without verification

**Blocks:** S6→S7 (if decision is irreversible), S7→S4 (if execution is irreversible)

**Condition:** `irreversibility >= 0.60 AND verification_passed == false`

`verification_passed` becomes true after:
* FSM-5 Verify completed, OR
* Explicit independent review recorded

### Guard G3: Adversarial requires monitoring loop

**Blocks:** S8→S9

**Condition:** `adversarial >= 0.60 AND monitoring_plan_exists == false`

### Guard G4: Institutional requires stakeholder/veto map

**Blocks:** S3→S7, S7→S8

**Condition:** `institutional >= 0.60 AND stakeholder_map_exists == false`

### Modifier injection

Instead of separate FSMs, treat danger archetypes as wrappers that inject required substates:

| Modifier | Injected substates |
|---|---|
| **Ambiguity (A)** | S1 must include: metric, scope, constraints. Create explicit `ProblemDefinition` artifact. |
| **Irreversibility (I)** | Gates: `IndependentReview`, `Pilot/Canary`, `RollbackPlan` (or explicit "none possible") |
| **Adversarial (D)** | `ThreatModel`, `DefenseInDepth`, `Detection/Response`, `IterationCadence` |
| **Institutional (P)** | `StakeholderMap`, `VetoPoints`, `CommsPlan`, `IncrementalRollout` |

These are graph nodes + checklist completion flags.

---

## Appendix: FSM Template Mapping from Control Patterns

> How the [canonical control patterns](control-pattern-taxonomy.md) map to FSM state templates.

### Branching templates

**Binary IF/ELSE:** S6_EVALUATE → S7_DECIDE (choose branch) → S3_PLAN for chosen branch. Guard: if condition depends on missing info → divert to S1_CLARIFY.

**Switch/Case:** Same as above but S7_DECIDE selects among N plans. Add "case coverage" check as a GUARD.

**Guarded decision:** Insert GUARD(preconditions) before S7_DECIDE or S4_EXECUTE. If guard fails → S1_CLARIFY or S5_OBSERVE or S3_PLAN depending on what's missing.

### Iteration templates

**FOR (enumerate options):** S3_PLAN (define candidate set) → S4_EXECUTE/S6_EVALUATE for each → S7_DECIDE (aggregate). Usually inside FSM-3 or FSM-4.

**WHILE (refine until done):** Loop: S2_MODEL → S3_PLAN → S4_EXECUTE → S5_OBSERVE → S6_EVALUATE → (back to S2 or S3). Stop condition: explicit `StopCriterion` artifact.

**DO–WHILE (act–observe–update):** S4_EXECUTE → S5_OBSERVE → S6_EVALUATE → (loop). Typical inside debug/optimize/adversarial.

### Recursion templates

**Decomposition recursion:** S2_MODEL creates subgoals/artifacts → spawn child traces or subgraphs. Each child runs its own FSM; parent does JOIN in S6_EVALUATE/S7_DECIDE.

**Meta-recursion (reflect):** Triggered when too many revision loops, contradictions, or repeated guard failures. Transition: S6_EVALUATE → S2_MODEL with a "process critique" artifact.

### Selection & ranking templates

**Filter:** S2_MODEL (constraints) → S6_EVALUATE (remove infeasible) → S3_PLAN (on remaining)

**Argmax/scoring:** S6_EVALUATE (compute scores) → S7_DECIDE (pick) → S8_HARDEN (document)

**Top-K shortlist:** Same as scoring but decision deferred; output is new candidate set artifact.

### Dependency & parallelism templates

**Sequential dependency:** Encode as DEPENDS_ON edges; enforce in FSM by only allowing S4_EXECUTE when deps satisfied.

**Parallel branches + join:** S3_PLAN spawns parallel subplans → run each → S6_EVALUATE join → S7_DECIDE

### Exception / escape templates

**Early exit:** Any state → S9_CLOSE when success criterion met (explicit `StopCriterion`)

**Fallback:** S4_EXECUTE fails → S6_EVALUATE → select fallback option → S4_EXECUTE

**Escalation:** S6_EVALUATE detects institutional/irreversible flags → ESCALATE artifact → S9_CLOSE or wait

---

## Implementation notes

* Store **FSM type** at trace level and chunk level.
* Store **state** for each step (node attribute).
* Store **transition edges** explicitly (`TRANSITION_TO` with reason).
* Learn "meta-thoughts" as:
  * Frequent subpaths inside an FSM
  * Cross-FSM handoffs (e.g., Clarify→Design→Operate; Debug→Operate; Verify→Decide)
