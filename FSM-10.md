Below is a clean collapse into **~10 universal FSMs** that cover the 15 archetypes. Each FSM is a reusable “meta-thought machine”: states, transitions, entry/exit criteria, and what to log in your graph.

I’m using a common state vocabulary so you can implement them uniformly:

* **S0 Intake**
* **S1 Clarify**
* **S2 Model**
* **S3 Plan**
* **S4 Execute**
* **S5 Observe**
* **S6 Evaluate**
* **S7 Decide**
* **S8 Harden**
* **S9 Close**

You can implement these as:

* a top-level FSM per session/trace
* nested sub-FSMs per chunk (windows of steps)

---

# FSM-1: Clarify & Frame (Problem Definition)

**Covers:** Ambiguity Resolution (12) + early stage of almost everything

**States**

* S0 Intake → S1 Clarify → S2 Model → S7 Decide → S9 Close

**Transitions**

* S0→S1 if goal/constraints are vague or conflicting
* S1→S2 once you have: objective, scope, success metric, constraints, stakeholders
* S2→S7 when you can choose: archetype + approach + next questions/plan
* S7→S9 when alignment is confirmed (or “insufficient info, stop”)

**Key outputs (graph artifacts)**

* `Goal{definition, metric, horizon}`
* `Scope{in,out}`
* `Constraints{hard,soft}`
* `Assumptions`
* `OpenQuestions`
* `ArchetypeLabel` (+ confidence)

**Exit criteria**

* “We all agree what success means” OR “cannot proceed without X”

---

# FSM-2: Diagnose & Fix (Debug Loop)

**Covers:** Diagnosis/Debugging (1)

**States**

* S0 Intake → S2 Model → S3 Plan → S4 Execute → S5 Observe → S6 Evaluate → (S3 or S8) → S9 Close

**Transitions**

* S0→S2 always (build causal model of failure)
* S2→S3 create ranked hypotheses
* S3→S4 run discriminating tests / reproduce / bisect
* S4→S5 capture observations
* S5→S6 update belief over hypotheses
* S6→S3 if ambiguity remains
* S6→S8 when root cause confirmed and fix chosen
* S8→S9 after verification + guardrails

**Graph signature**

* Repeating cycle: `Hypothesis → Test → Observation → Update`
* Node types: `Symptom`, `Hypothesis`, `Test`, `Evidence`, `RootCause`, `Fix`, `RegressionTest`

**Exit criteria**

* Root cause confirmed + fix verified + monitor/guardrail added

---

# FSM-3: Design & Decide (Constraint-Satisfying Design Funnel)

**Covers:** Design under constraints (2) + many decisions (5)

**States**

* S0 Intake → S1 Clarify → S2 Model → S3 Plan → S7 Decide → S8 Harden → S9 Close

**Transitions**

* S1→S2 produce requirements model + constraints map
* S2→S3 generate options, tradeoff criteria, evaluation plan
* S3→S7 after evaluating 2–5 viable options
* S7→S8 once a design is selected (interfaces, ADRs, rollout)
* S8→S9 once deliverables and owners exist

**Graph artifacts**

* `Option` nodes with `Pros/Cons`, `Cost`, `Risk`
* `Constraint` nodes + `Violates` edges
* `Decision` node with `Rationale`

**Exit criteria**

* Decision recorded + implementation plan exists

---

# FSM-4: Optimize (Experiment Loop)

**Covers:** Optimization (3)

**States**

* S0 Intake → S2 Model → S3 Plan → S4 Execute → S5 Observe → S6 Evaluate → (S3 or S9)

**Transitions**

* S2 defines metric model + levers
* S3 picks highest ROI experiment
* S6→S3 if more headroom
* S6→S9 if diminishing returns or risk threshold reached

**Graph artifacts**

* `Metric`, `Baseline`, `Intervention`, `Result`, `Regression`, `Decision(keep/revert)`

**Exit criteria**

* Metric target met OR marginal gain too small OR risk too high

---

# FSM-5: Verify (Claim Testing / Audit)

**Covers:** Validation/Verification (9) + part of one-way-door (15)

**States**

* S0 Intake → S1 Clarify → S2 Model → S3 Plan → S4 Execute → S5 Observe → S6 Evaluate → S9 Close

**Transitions**

* S1 pin down exact claim + acceptance threshold
* S2 enumerate assumptions + falsifiers
* S3 design independent tests/replications
* S6 concludes with calibrated confidence (not just yes/no)

**Graph artifacts**

* `Claim`, `Assumption`, `Falsifier`, `TestPlan`, `Replication`, `Confidence`

**Exit criteria**

* Confidence statement + evidence trail + known limits

---

# FSM-6: Transform (Translation with Invariants)

**Covers:** Translation/Transformation (6)

**States**

* S0 Intake → S1 Clarify → S2 Model → S3 Plan → S4 Execute → S6 Evaluate → (S4 or S9)

**Transitions**

* S1 define target format + invariants + oracle tests
* S2 map source→target constructs
* S4 do incremental transforms
* S6 validate equivalence continuously; loop until done

**Graph artifacts**

* `Invariant`, `OracleTest`, `Mapping`, `MigrationStep`, `EquivalenceCheck`

**Exit criteria**

* Target produced + invariants satisfied + rollback path (if relevant)

---

# FSM-7: Operate & Harden (Productionization)

**Covers:** Operationalization/Productionization (10) + part of design (2)

**States**

* S0 Intake → S2 Model → S3 Plan → S4 Execute → S5 Observe → S6 Evaluate → S8 Harden → S9 Close

**Transitions**

* S2 identify failure modes + SLO/SLA
* S3 define monitoring/alerting/runbooks/rollout
* S4 implement reliability features + deploy staged
* S8 finalize ownership, docs, rollback, on-call readiness

**Graph artifacts**

* `SLO`, `FailureMode`, `Monitor`, `Alert`, `Runbook`, `RolloutStep`, `Owner`

**Exit criteria**

* Production readiness criteria satisfied

---

# FSM-8: Postmortem & Prevent (Backwards Causality)

**Covers:** Failure analysis/post-mortem (8)

**States**

* S0 Intake → S2 Model → S5 Observe → S6 Evaluate → S8 Harden → S9 Close

**Transitions**

* S2 builds timeline/causal model (backwards)
* S5 collects evidence
* S6 separates root causes vs contributing factors
* S8 creates preventive/detective actions + owners

**Graph artifacts**

* `TimelineEvent`, `Trigger`, `Impact`, `RootCause`, `ContribFactor`, `ActionItem`

**Exit criteria**

* Action items with owners + follow-up date; learning recorded as pattern

---

# FSM-9: Resolve Conflicts (Constraint Arbitration)

**Covers:** Constraint conflict resolution (7) + institutional/one-way-door interactions

**States**

* S0 Intake → S1 Clarify → S2 Model → S3 Plan → S7 Decide → S9 Close

**Transitions**

* S1: enumerate constraints + authority levels
* S2: prove infeasibility / conflict
* S3: generate compromise packages + scope/time adjustments
* S7: escalate to authority when needed; record decision

**Graph artifacts**

* `Constraint`, `Authority`, `Conflict`, `CompromiseOption`, `Escalation`, `Decision`

**Exit criteria**

* Tradeoff accepted by authority + residual risk documented

---

# FSM-10: Adversarial Adaptation (Threat-Defense Loop)

**Covers:** Adversarial/strategic problems (13)

**States**

* S0 Intake → S2 Model → S3 Plan → S4 Execute → S5 Observe → S6 Evaluate → (S3 or S8) → S9 Close

**Transitions**

* S2 define adversary model + incentives + capabilities
* S3 design defense-in-depth + detection/response
* S6 update model based on observed adaptation
* S8 harden monitoring + iteration cadence

**Graph artifacts**

* `Adversary`, `Attack`, `Defense`, `Detection`, `Response`, `GameLoop`

**Exit criteria**

* Robust baseline defense + monitoring + iteration plan (never “done forever”)

---

## Where did “Institutional/Political” and “Irreversibility” go?

They’re **not separate FSMs**; they’re **global modifiers** that wrap any FSM:

### Modifier A: Institutional Navigation (for any FSM)

Add states/edges:

* `StakeholderMap`, `VetoPoint`, `Coalition`, `CommsPlan`
  Common insertion: between S3 Plan and S7 Decide (and again before S8 Harden)

### Modifier B: One-way Door Gating (for any FSM)

Add gates:

* `IndependentReview`, `Redundancy`, `Pilot`, `Signoff`
  Common insertion: before any irreversible transition (usually before S4 Execute or S7 Decide)

This keeps you at ~10 FSMs while still covering the last 5%.

---

## Implementation notes for your graph + embeddings

* Store **FSM type** at trace level and chunk level.
* Store **state** for each step (node attribute).
* Store **transition edges** explicitly (`TRANSITION_TO` with reason).
* Learn “meta-thoughts” as:

  * frequent subpaths inside an FSM
  * cross-FSM handoffs (e.g., Clarify→Design→Operate; Debug→Operate; Verify→Decide)

If you want, next you can ask for: the unified schema (node/edge types + properties) that supports all 10 FSMs cleanly.
