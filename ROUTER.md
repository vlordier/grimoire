Below is a **concrete, implementable design** for an **early routing classifier** whose only job is to detect **danger archetypes early** and throttle / redirect the FSM *before* damage is done.

This is not a generic “intent classifier”. It’s a **risk gate**.

---

# 0) What this classifier is (and is not)

**It is**

* Early (runs on first problem statement + first 1–2 turns)
* Conservative (high recall > high precision)
* Multi-label (more than one danger can be present)
* Used to **slow down / change procedure**, not to answer

**It is NOT**

* A domain classifier
* A solution selector
* A confidence estimator

Output is *procedural control*, not content.

---

# 1) The four danger archetypes (operational definition)

We detect these **orthogonally** (independent scores):

| Danger archetype    | Core risk                                    |
| ------------------- | -------------------------------------------- |
| **Ambiguity**       | Solving the wrong problem                    |
| **Adversarial**     | Opponent adapts, static solution fails       |
| **Irreversibility** | Mistakes are costly or non-recoverable       |
| **Institutional**   | Power/optics block technically correct paths |

Each has:

* **signals**
* **questions to force**
* **FSM modifiers**

---

# 2) Inputs to the classifier

### Minimal input (early-safe)

* Initial problem statement
* Optional: first clarification reply from assistant
* Optional metadata:

  * domain
  * user role (if known)
  * deployment context (prod / research / advice)

No tools, no browsing, no long reasoning.

---

# 3) Feature extraction (cheap, robust)

### A) Lexical / structural signals (fast, rule-heavy)

These catch 70% cheaply.

**Ambiguity**

* Vague verbs: *improve, make better, handle, ensure*
* Missing objects: “make it scalable” (no scale)
* Missing metrics/time horizon
* Conflicting adjectives: *fast and safe and cheap*
* Pronouns without referents: *it, this system*

**Adversarial**

* Words: *attack, fraud, abuse, spam, bypass, evade*
* Mentions of users acting strategically
* Security / moderation / incentives language

**Irreversibility**

* Words: *legal, medical, safety, compliance, irreversible*
* Phrases: *no rollback, cannot undo, one chance*
* High-stakes nouns: *patients, lives, court, regulation*

**Institutional**

* Mentions of:

  * boards, regulators, committees
  * public sector
  * large orgs
  * approvals, sign-off, optics, politics
* Passive constraints: *“they won’t allow…”*

---

### B) Semantic probes (LLM, shallow)

Ask the model **internally** to answer *binary probes* (not chain-of-thought):

Examples:

* “Is the success criterion clearly defined?”
* “Would another agent benefit from defeating this solution?”
* “Would an incorrect decision cause irreversible harm?”
* “Is the technically best solution likely blocked by authority or politics?”

Each probe → yes/no + confidence.

---

### C) Structural absence signals (very important)

These detect *what’s missing*, not what’s said.

| Missing thing   | Implies         |
| --------------- | --------------- |
| No metric       | Ambiguity       |
| No rollback     | Irreversibility |
| No stakeholder  | Institutional   |
| No threat model | Adversarial     |

---

# 4) Scoring model (simple, transparent)

Use **independent scores** in [0,1].

Example (pseudo):

```
ambiguity_score =
  w1 * vague_language
+ w2 * missing_metric
+ w3 * conflicting_constraints
+ w4 * semantic_probe_uncertainty
```

Same for others.

**Thresholds**

* ≥0.3 → *present*
* ≥0.6 → *dominant*
* ≥0.8 → *critical*

Do **not** softmax. These are not mutually exclusive.

---

# 5) Routing decisions (this is the core)

The classifier does **not** choose a solution FSM.
It applies **procedural modifiers**.

## A) Ambiguity detected

**Effect**

* Force FSM-1 (Clarify & Frame)
* Block execution/design/debug FSMs

**Injected steps**

* Ask 3–5 discriminating questions
* Require:

  * success metric
  * scope (in/out)
  * constraints (hard/soft)

**Autonomy**

* LOW
* No speculative solutions allowed

---

## B) Adversarial detected

**Effect**

* Route to FSM-10 (Adversarial Adaptation) or wrap current FSM with adversarial modifier

**Injected steps**

* Explicit adversary model
* Incentive analysis
* Detection + monitoring requirement

**Autonomy**

* MEDIUM
* No “optimal” static solutions allowed
* Must include iteration loop

---

## C) Irreversibility detected

**Effect**

* Add **gates** to any FSM

**Injected steps**

* Worst-case analysis
* Independent verification (FSM-5)
* Rollback / pilot requirement OR explicit acknowledgment of no rollback

**Autonomy**

* VERY LOW
* Conservative bias enforced
* No single-shot decisions

---

## D) Institutional detected

**Effect**

* Wrap FSM with institutional modifier

**Injected steps**

* Stakeholder map
* Veto-point identification
* Incremental path required
* Communication plan

**Autonomy**

* MEDIUM–LOW
* Technically optimal but infeasible paths flagged as such

---

# 6) Combined cases (very common)

### Ambiguity + Irreversibility (extremely dangerous)

→ Clarify first **and** slow down
→ No execution until definitions + sign-off

### Adversarial + Institutional

→ Expect policy gaming
→ Require monitoring + audit trail

### All four present

→ Escalation mode

* No autonomous execution
* Decision support only
* Explicit uncertainty surfaced

---

# 7) Output schema (what your system emits)

Example:

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

# 8) Training data (where it comes from)

You do **not** need huge labeled datasets.

* Hand-label ~300–500 problem statements
* Label presence (yes/no) for each danger archetype
* Use:

  * weak rules for bootstrapping
  * small supervised head or LLM-based classifier
* Actively learn: false negatives are more expensive than false positives

---

# 9) Evaluation metric (important)

Do **not** optimize accuracy.

Optimize:

* **Recall on dangerous cases**
* **Time-to-intervention** (how early detected)
* **Reduction in bad FSM transitions** (e.g. executing before clarifying)

---

# 10) Why this works

This classifier mirrors what **senior humans do instinctively**:

* “Wait—what exactly do you mean?”
* “Careful, this is safety-critical.”
* “People will fight this.”
* “Attackers will adapt.”

You are making that instinct **explicit, programmable, and enforceable**.
