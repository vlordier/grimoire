# Danger Classification

> Design for the early danger-archetype routing classifier. For how these scores feed into FSM transition guards, see [FSM Catalogue — Transition Guards](fsm-catalogue.md#transition-guards). For the Python reference implementation, see [Danger Classification Implementation](../reference/danger-classification-impl.md).
>
> **See also:** [Problem Archetypes](problem-archetypes.md) (archetypes 12–15 are the four danger archetypes) · [Canonical Schemas](../reference/canonical-schemas.md) (`DangerType`, `DangerScores`)

---

## 0. What this classifier is (and is not)

**It is:**
* Early (runs on first problem statement + first 1–2 turns)
* Conservative (high recall > high precision)
* Multi-label (more than one danger can be present)
* Used to **slow down / change procedure**, not to answer

**It is NOT:**
* A domain classifier
* A solution selector
* A confidence estimator

Output is *procedural control*, not content.

---

## 1. The four danger archetypes

Detected **orthogonally** (independent scores):

| Danger archetype    | Core risk                                    |
| ------------------- | -------------------------------------------- |
| **Ambiguity**       | Solving the wrong problem                    |
| **Adversarial**     | Opponent adapts, static solution fails       |
| **Irreversibility** | Mistakes are costly or non-recoverable       |
| **Institutional**   | Power/optics block technically correct paths |

Each has: signals, questions to force, and FSM modifiers.

---

## 2. Inputs

### Minimal input (early-safe)

* Initial problem statement
* Optional: first clarification reply from assistant
* Optional metadata: domain, user role (if known), deployment context (prod / research / advice)

No tools, no browsing, no long reasoning.

---

## 3. Feature extraction

### A) Lexical / structural signals (fast, rule-heavy)

Catches ~70% cheaply.

**Ambiguity signals:**
* Vague verbs: *improve, better, enhance, optimize, increase, reduce, make, handle, support, enable, ensure*
* Vague quality adjectives: *scalable, robust, reliable, secure, safe, fast, efficient, user-friendly, production-ready*
* Missing object patterns: "make it …", "improve it …", "handle this …"
* No-metric hint: if no metric token found and vague verbs/adjectives present → ambiguity up
* Conflicting constraints: co-occurrence of *fast/low latency* + *cheap/low cost* + *high accuracy/reliable/safe/secure*

**Adversarial signals:**
* Terms: *adversary, attack, bypass, evade, abuse, fraud, spam, bots, cheat, exploit, poisoning, prompt injection, jailbreak, DDoS, phishing, malware, red team*
* Trust & safety: *content moderation, trust and safety, T&S*
* Incentives language: *incentive, gamed/gaming, arms race, cat-and-mouse, adaptive, strategic*

**Irreversibility signals:**
* High-stakes domains: *medical, patient, clinical, diagnosis, treatment, drug, dose, legal, court, lawsuit, compliance, regulatory, safety-critical, aviation, automotive, nuclear, financial advice, credit decision*
* No-rollback language: *irrevocable, irreversible, cannot undo, no rollback, one-way door, point of no return, permanent*
* Harm terms: *life, death, harm, injury, liability, fines, penalties, prison, reputational damage*

**Institutional signals:**
* Stakeholder/authority words: *board, committee, leadership, execs, legal team, procurement, union, works council, regulator, auditor, compliance, risk team, security team, stakeholders*
* Politics/optics: *politics, optics, narrative, buy-in, alignment, approval, sign-off, veto, governance, bureaucracy, public sector*
* Blocked-by-org phrasing: *they won't, they refuse, not allowed, forbidden, blocked, cannot get approval*

### B) Semantic probes (LLM, shallow)

Ask the model **internally** to answer binary probes (not chain-of-thought):

**Ambiguity probes:**
* "Is the success criterion (metric + target + horizon) explicitly defined?"
* "Is scope clearly defined (in/out)?"
* "Are constraints clearly listed?"

**Adversarial probes:**
* "Is there an agent that may try to evade, exploit, or adapt to the solution?"
* "Is this in security, fraud, abuse, moderation, or competitive setting?"

**Irreversibility probes:**
* "Would an error cause serious harm, legal exposure, or be hard to roll back?"
* "Is a rollback/pilot feasible?"

**Institutional probes:**
* "Are approvals, politics, optics, or governance likely to be the binding constraint?"
* "Is there a named authority/veto holder involved?"

Implementation: ask the model to output strict JSON: `{probe_id, answer: "yes"|"no", confidence: 0..1}`

### C) Structural absence signals

Detect *what's missing*, not what's said:

| Missing thing   | Implies         |
| --------------- | --------------- |
| No metric       | Ambiguity       |
| No rollback     | Irreversibility |
| No stakeholder  | Institutional   |
| No threat model | Adversarial     |

---

## 4. Scoring model

Use **independent scores** in [0,1] per archetype. Each archetype has its own formula with different coefficients and terms:

### Ambiguity (5 terms)

```
ambiguity = clip01(
    0.18 * regex_hits
  + 0.25 * absence          // missing metric tokens AND regex hits > 0
  + 0.12 * conflict          // conflicting constraints (fast + cheap + safe ≥ 2)
  + 0.22 * (1 − probe_success_defined)
  + 0.23 * (1 − probe_scope_defined)
)
```

Note: ambiguity uses **inverted** probe scores (high when probes say "no, not defined").

### Adversarial (2 terms)

```
adversarial = clip01(0.18 * regex_hits + 0.50 * probe_adaptive_agent)
```

### Irreversibility (2 terms)

```
irreversibility = clip01(0.18 * regex_hits + 0.55 * probe_hard_to_rollback)
```

### Institutional (2 terms)

```
institutional = clip01(0.18 * regex_hits + 0.55 * probe_power_blocks)
```

Where:
* `regex_hits`: count of matched patterns per archetype (cap at 5)
* `absence` ∈ {0,1}: missing metric tokens when vague verbs present
* `conflict` ∈ {0,1}: co-occurrence of competing constraints (fast/cheap/safe)
* `probe_*` ∈ [0,1]: LLM probe confidence (see §3B)

> For the implementation, see [Danger Classification Implementation — `score_dangers()`](../reference/danger-classification-impl.md).

**Thresholds:**
* ≥ 0.30 → *present*
* ≥ 0.60 → *dominant*
* ≥ 0.80 → *critical*

Do **not** softmax. These are not mutually exclusive.

**Store both:** `danger_scores` (4 floats) + `evidence` (top regex hits + probe answers) for debuggability.

---

## 5. Routing decisions

The classifier does **not** choose a solution FSM. It applies **procedural modifiers**.

### A) Ambiguity detected

* **Effect:** Force FSM-1 (Clarify & Frame). Block execution/design/debug FSMs.
* **Injected steps:** Ask 3–5 discriminating questions. Require: success metric, scope (in/out), constraints (hard/soft).
* **Autonomy:** LOW. No speculative solutions allowed.

### B) Adversarial detected

* **Effect:** Route to FSM-10 (Adversarial Adaptation) or wrap current FSM with adversarial modifier.
* **Injected steps:** Explicit adversary model. Incentive analysis. Detection + monitoring requirement.
* **Autonomy:** MEDIUM. No "optimal" static solutions allowed. Must include iteration loop.

### C) Irreversibility detected

* **Effect:** Add gates to any FSM.
* **Injected steps:** Worst-case analysis. Independent verification (FSM-5). Rollback / pilot requirement OR explicit acknowledgment of no rollback.
* **Autonomy:** VERY LOW. Conservative bias enforced. No single-shot decisions.

### D) Institutional detected

* **Effect:** Wrap FSM with institutional modifier.
* **Injected steps:** Stakeholder map. Veto-point identification. Incremental path required. Communication plan.
* **Autonomy:** MEDIUM–LOW. Technically optimal but infeasible paths flagged as such.

---

## 6. Combined cases

### Ambiguity + Irreversibility (extremely dangerous)
→ Clarify first **and** slow down → No execution until definitions + sign-off

### Adversarial + Institutional
→ Expect policy gaming → Require monitoring + audit trail

### All four present
→ Escalation mode:
* No autonomous execution
* Decision support only
* Explicit uncertainty surfaced

---

## 7. Output schema

```json
{
  "danger_archetypes": {
    "ambiguity": { "score": 0.72, "status": "dominant" },
    "adversarial": { "score": 0.15, "status": "absent" },
    "irreversibility": { "score": 0.61, "status": "dominant" },
    "institutional": { "score": 0.44, "status": "present" }
  },
  "routing_actions": [
    "FORCE_FSM_CLARIFY",
    "ADD_IRREVERSIBLE_GATES",
    "REQUIRE_STAKEHOLDER_MAP"
  ],
  "autonomy_level": "LOW",
  "blocked_actions": ["EXECUTE", "DECIDE"]
}
```

This is **machine-actionable**.

---

## 8. Training data

No huge labeled datasets needed:

* Hand-label ~300–500 problem statements
* Label presence (yes/no) for each danger archetype
* Use:
  * Weak rules for bootstrapping
  * Small supervised head or LLM-based classifier
* Actively learn: false negatives are more expensive than false positives

---

## 9. Evaluation metric

Do **not** optimize accuracy. Optimize:

* **Recall on dangerous cases**
* **Time-to-intervention** (how early detected)
* **Reduction in bad FSM transitions** (e.g. executing before clarifying)

---

## 10. Why this works

This classifier mirrors what **senior humans do instinctively**:

* "Wait—what exactly do you mean?"
* "Careful, this is safety-critical."
* "People will fight this."
* "Attackers will adapt."

This instinct is made **explicit, programmable, and enforceable**.

---

## Day-1 implementation plan

1. **Implement `danger_regex_features(text)`** — returns counts + flags: `has_metric_tokens`, `cooccur_fast_cheap_safe`, hit lists per archetype
2. **Implement `danger_probes(text)`** (4–8 probes total) — strict JSON output, cache results per text hash
3. **Implement `danger_score(features, probes)`** — compute 4 scores + evidence
4. **Integrate with FSM engine** — create `DangerContext` on trace start, add guards G1–G4 to transition table, add checklist flags that get set as conversation proceeds
5. **Test with 50–100 hand examples** — aim for high recall, false positives are acceptable (they just cause extra questions)

### Tiny behavior example

**Input:** "Make our model safer and scalable for production."

**Classifier output:**
* Ambiguity: high (vague + no metrics)
* Irreversibility: medium (if "safer" triggers)
* Institutional: low (unless stakeholders mentioned)

**Routing:** Force FSM-1 (Clarify). Block execute/design until definition complete.
