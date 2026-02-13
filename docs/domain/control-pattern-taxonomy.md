# Control Pattern Taxonomy

> Canonical set of procedural control patterns — the "instruction set" of reasoning. For how these map to the 10 universal FSMs, see [FSM Catalogue](fsm-catalogue.md). For auto-detection and mining from raw traces, see [Pattern Detection & Pipeline](../reference/pattern-detection-and-pipeline.md).
>
> **See also:** [Problem Archetypes](problem-archetypes.md) · [Danger Classification](danger-classification.md) · [System Architecture](../architecture/system-architecture.md) · [Canonical Schemas](../reference/canonical-schemas.md)

---

## 1. Branching (decision-making)

### 1.1 Binary decision (IF / ELSE)

| Aspect | Detail |
|---|---|
| **Pattern** | Evaluate condition → choose exactly one path |
| **Meta-use** | Feasibility checks · go/no-go decisions · constraint satisfaction |
| **Failure mode** | Condition ill-defined · premature decision under ambiguity |

### 1.2 Multi-way decision (SWITCH / CASE)

| Aspect | Detail |
|---|---|
| **Pattern** | Evaluate discriminator → select one of N mutually exclusive paths |
| **Meta-use** | Strategy selection · architecture choice · policy routing |
| **Failure mode** | Missing cases · wrong discriminator variable |

### 1.3 Guarded decision (IF with preconditions)

| Aspect | Detail |
|---|---|
| **Pattern** | Check safety/validity conditions → only then allow downstream action |
| **Meta-use** | Safety gating · compliance checks · FSM guards |
| **Failure mode** | Guards missing or bypassed |

---

## 2. Iteration (loops)

### 2.1 Fixed iteration (FOR loop)

| Aspect | Detail |
|---|---|
| **Pattern** | Iterate over a known finite set |
| **Meta-use** | Enumerating options · comparing candidates · exhaustive checks |
| **Failure mode** | Wrong iteration space · combinatorial explosion |

### 2.2 Condition-controlled iteration (WHILE loop)

| Aspect | Detail |
|---|---|
| **Pattern** | Repeat until condition met |
| **Meta-use** | Refinement · optimization · debugging |
| **Failure mode** | Non-termination · vague stopping condition |

### 2.3 Observe–update loop (DO–WHILE)

| Aspect | Detail |
|---|---|
| **Pattern** | Act → observe → update → repeat |
| **Meta-use** | Experiments · model fitting · hypothesis testing |
| **Failure mode** | No learning signal · no convergence criterion |

---

## 3. State-based control (FSM logic)

### 3.1 Finite State Machine

| Aspect | Detail |
|---|---|
| **Pattern** | Explicit states · allowed transitions only |
| **Meta-use** | Multi-step processes · regulated workflows · safety-critical reasoning |
| **Failure mode** | Hidden state · invalid transitions |

### 3.2 Hierarchical FSM

| Aspect | Detail |
|---|---|
| **Pattern** | States composed of sub-states |
| **Meta-use** | Complex workflows · nested procedures |
| **Failure mode** | Over-complexity · poor abstraction boundaries |

---

## 4. Recursion (self-reference)

### 4.1 Structural recursion

| Aspect | Detail |
|---|---|
| **Pattern** | Solve problem by solving smaller instances |
| **Meta-use** | Decomposition · divide-and-conquer · proofs |
| **Failure mode** | No base case · infinite regress |

### 4.2 Meta-recursion (reasoning about reasoning)

| Aspect | Detail |
|---|---|
| **Pattern** | Inspect and revise the reasoning process itself |
| **Meta-use** | Debugging · reflection · strategy correction |
| **Failure mode** | Analysis paralysis · endless self-critique |

---

## 5. Selection & ranking

### 5.1 Filter

| Aspect | Detail |
|---|---|
| **Pattern** | Remove invalid candidates |
| **Meta-use** | Constraint enforcement · feasibility pruning |

### 5.2 Rank / Argmax

| Aspect | Detail |
|---|---|
| **Pattern** | Score options → select best |
| **Meta-use** | Optimization · tradeoff analysis |
| **Failure mode** | Wrong objective · uncalibrated scoring |

### 5.3 Top-K shortlist

| Aspect | Detail |
|---|---|
| **Pattern** | Keep small candidate set · defer final decision |
| **Meta-use** | Decision under uncertainty · exploration vs. exploitation |

---

## 6. Dependency control

### 6.1 Sequential dependency

| Aspect | Detail |
|---|---|
| **Pattern** | Step B depends on output of A |
| **Meta-use** | Pipelines · causal reasoning |

### 6.2 Conditional dependency

| Aspect | Detail |
|---|---|
| **Pattern** | Dependency exists only if condition holds |
| **Meta-use** | Optional steps · contingency planning |

### 6.3 Parallel branches with join

| Aspect | Detail |
|---|---|
| **Pattern** | Execute branches independently → merge results |
| **Meta-use** | Comparative analysis · ensemble reasoning |

---

## 7. Exception & escape patterns

### 7.1 Early exit (BREAK / RETURN)

| Aspect | Detail |
|---|---|
| **Pattern** | Terminate early when condition met |
| **Meta-use** | Fast failure · cost control |

### 7.2 Fallback

| Aspect | Detail |
|---|---|
| **Pattern** | Primary path fails → secondary path |
| **Meta-use** | Robustness · degraded modes |

### 7.3 Escalation

| Aspect | Detail |
|---|---|
| **Pattern** | Hand off to higher authority or different system |
| **Meta-use** | Institutional constraints · human-in-the-loop |

---

## 8. Knowledge update patterns

### 8.1 Hypothesis → test → update

| Aspect | Detail |
|---|---|
| **Pattern** | Propose → test → revise belief |
| **Meta-use** | Scientific reasoning · debugging |

### 8.2 Bayesian update (generalized)

| Aspect | Detail |
|---|---|
| **Pattern** | Prior → evidence → posterior |
| **Meta-use** | Uncertainty handling · risk assessment |

---

## 9. Control of uncertainty

### 9.1 Clarify-before-act

| Aspect | Detail |
|---|---|
| **Pattern** | Delay action until ambiguity reduced |
| **Meta-use** | High-risk domains · requirements gathering |

### 9.2 Safe-to-fail experiment

| Aspect | Detail |
|---|---|
| **Pattern** | Small reversible action → learn cheaply |
| **Meta-use** | Exploration · prototyping |

---

## 10. Meta-control (the system's differentiator)

### 10.1 Autonomy throttling

| Aspect | Detail |
|---|---|
| **Pattern** | Adjust allowed actions based on danger |
| **Meta-use** | Safety systems · governance |

### 10.2 Guarded execution

| Aspect | Detail |
|---|---|
| **Pattern** | Execute only if invariants hold |
| **Meta-use** | Prevent catastrophic errors |

---

## Canonical compression

All 10 groups collapse into **6 fundamental control primitives**:

| # | Primitive | Covers groups |
|---|-----------|---------------|
| 1 | **Branch** — choose path | §1 Branching |
| 2 | **Loop** — repeat | §2 Iteration, §4 Recursion (recursion is iteration with a stack) |
| 3 | **State transition** — where am I allowed to go | §3 FSM logic, §6 Dependency control (dependency ordering is allowed-transition logic) |
| 4 | **Select** — filter / rank | §5 Selection & ranking |
| 5 | **Update belief** — learn | §8 Knowledge update, §9 Uncertainty control |
| 6 | **Abort / Escalate** — stop safely | §7 Exception & escape, §10 Meta-control |

**Core insight:** Reasoning traces are programs written in these primitives, and meta-thoughts are reusable subroutines over them.

---

## Formal minimal algebra

Treat a reasoning trace as a program over a small set of typed operators.

### Types

| Symbol | Meaning |
|--------|---------|
| σ | Structured working memory (goals, constraints, beliefs, artifacts, open questions, danger scores) |
| o | Observation — any evidence (tool output, user answer, metric, quote) |
| a | Action — any external operation (tool call, deploy, config change) |
| d | Discrete choice among options |
| b | Distribution or score vector over hypotheses/options |
| A | Artifact — goal / constraint / assumption / test / metric |

A trace is a sequence of operators that transform σ.

### Minimal operator set

| Operator | Signature | Semantics |
|----------|-----------|-----------|
| `ASSERT(φ)` | σ → σ | Add a claim/constraint/assumption φ into state (typed, with provenance) |
| `ASK(q)` | σ → σ' | Emit a question; update σ with an open slot q |
| `OBSERVE(o)` | σ → σ | Add evidence to state, link it to claims/hypotheses |
| `BRANCH(cond, P_true, P_false)` | σ → σ | Conditional control flow; cond evaluable from σ or from a probe |
| `SELECT(S, score, k)` | σ → (σ, S') | Filter/rank candidates S using scoring functional; return top-k S' |
| `ITERATE(stop, body)` | σ → σ | General loop; stop(σ) decides termination; body is a subprogram |
| `UPDATE(b, o)` | σ → σ | Belief update (Bayesian-ish, heuristic, or rule-based) |
| `EXECUTE(a)` | σ → σ | Perform an action or tool call; yields observation(s) later via OBSERVE |
| `GUARD(pre)` | σ ↛ σ | If pre(σ) fails, transition is blocked and emits required subgoals |
| `HALT(reason)` | σ → σ_final | Stop |
| `ESCALATE(to, reason)` | σ → σ | Hand off to higher authority or different system |

### Composition rules

* **Sequencing:** `(P ; Q)(σ) = Q(P(σ))`
* Programs are ASTs built from these operators
* **Patterns** are frequent subtrees / subpaths in this algebra

### Why this is useful for learning

1. Map text → operator sequence `(op_t)` + arguments
2. Mine frequent operator n-grams / motifs
3. Learn a policy `π(σ) → next_op` constrained by `GUARD`
