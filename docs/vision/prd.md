# Product Requirements Document (PRD)

> **See also:** [Executive Summary](prd-executive.md) · [Project Specification](spec.md) · [System Architecture](../architecture/system-architecture.md) · [Capability Requirements](../architecture/capability-requirements.md) · [Build Plan](../architecture/build-plan.md)

## Product name

**Grimoire**
*Also known as:* Meta-Thought Engine (MTE)
*Subtitle*: Procedural intelligence over reasoning traces

---

## 1. Problem statement

Most AI systems treat reasoning as **opaque text** or **static embeddings**.
As a result, they:

* repeat known mistakes (premature execution, unclear goals),
* fail on high-risk problems (irreversible, adversarial, institutional),
* cannot reuse reasoning strategies across domains,
* cannot explain *why* a certain reasoning path was chosen.

Humans, by contrast, reuse a small set of **procedural patterns** ("meta-thoughts") across most problems.

**The problem:** There is no system that explicitly models, stores, retrieves, and enforces *procedural reasoning patterns* at scale.

---

## 2. Product vision

Build a system that:

* converts raw reasoning traces into **structured procedural knowledge**,
* detects **problem archetypes and dangers early**,
* routes reasoning through **validated finite-state procedures**,
* reuses **meta-thoughts** across domains,
* and prevents catastrophic reasoning errors by design.

This is not a chatbot.
This is a **procedural intelligence layer**.

---

## 3. Target users

### Primary users

* AI researchers and engineers
* Agent / toolchain builders
* Safety, governance, and evaluation teams
* Advanced product / platform teams

### Secondary users

* Technical decision-makers (architecture, ML, infra)
* Organizations building autonomous or semi-autonomous systems

---

## 4. What the product does (core outcome)

### At the end of this project, the system will:

1. **Ingest reasoning traces**

   * From Hugging Face datasets, logs, conversations, tools
   * Normalize them into a canonical schema

2. **Model reasoning explicitly**

   * Steps, states, artifacts, constraints, decisions
   * Stored as a graph (Neo4j)

3. **Index reasoning semantically**

   * Steps, step-windows, and patterns stored in a vector DB (Qdrant)

4. **Detect danger archetypes early**

   * Ambiguity
   * Adversarial dynamics
   * Irreversibility
   * Institutional / political constraints

5. **Route reasoning through FSMs**

   * 10 universal finite-state machines
   * Guards prevent invalid transitions (e.g. execute before clarify)

6. **Extract and reuse meta-thoughts**

   * Debug loops
   * Design funnels
   * Verification gates
   * Adversarial defense cycles
   * Institutional navigation patterns

7. **Recommend next procedural steps**

   * Not "answers"
   * But *what kind of step should happen next*, with a template

---

## 5. What the product is NOT

* ❌ Not a general LLM
* ❌ Not a chat UI (initially)
* ❌ Not a symbolic planner for arbitrary domains
* ❌ Not a replacement for human judgment in high-stakes cases

It is a **control and reuse layer** over reasoning.

---

## 6. Key user journeys

### Journey 1 — New problem routing

1. User submits a problem statement
2. System detects danger archetypes
3. FSM + guards are selected
4. System either:

   * asks clarifying questions
   * inserts verification gates
   * or allows execution planning

**Outcome:** fewer wrong first steps.

---

### Journey 2 — Procedural reuse

1. System sees a partial reasoning context
2. Retrieves similar **procedural patterns**
3. Suggests a proven meta-thought
4. Explains why it applies

**Outcome:** faster convergence, less thrashing.

---

### Journey 3 — Safety / governance audit

1. Inspect a trace
2. See which FSM was active
3. See which guards fired
4. See why a decision was blocked or allowed

**Outcome:** explainability and auditability.

---

## 7. Functional requirements

### FR-1 Canonical schema

* Unified representation for traces, steps, artifacts, patterns
* Versioned and auditable

### FR-2 Graph storage

* Steps and relations in Neo4j
* Traversable reasoning structure

### FR-3 Vector retrieval

* Step-level, window-level, pattern-level embeddings
* Filterable by FSM, danger, domain

### FR-4 Danger router

* Regex + probe-based classifier
* High recall on dangerous cases
* Multi-label output

### FR-5 FSM execution engine

* State tracking
* Transition guards
* Modifiers for danger archetypes

### FR-6 Pattern mining

* FSM subpaths
* Graph motifs
* Semantic clusters

### FR-7 Next-step recommender

* Pattern retrieval + filtering
* Template-based suggestions
* Autonomy throttling

---

## 8. Non-functional requirements

### Safety

* Dangerous transitions must be blockable
* Conservative defaults
* Explicit uncertainty surfacing

### Explainability

* Every recommendation traceable to:

  * FSM
  * Pattern
  * Danger assessment

### Performance

* Routing + retrieval < 200ms (excluding embeddings)
* Scales to millions of steps

### Extensibility

* New FSMs, dangers, artifacts pluggable
* New datasets ingestible without schema change

---

## 9. Success metrics

### Core metrics

* **Danger recall** (target >90%)
* **Invalid transition prevention rate**
* **Reduction in revision loops**
* **Time to problem clarification**

### Secondary metrics

* Pattern reuse frequency
* Pattern success proxy improvement over time
* Human evaluation of next-step usefulness

---

## 10. Final outcome (one sentence)

> **A reusable, auditable, and safety-aware procedural intelligence engine that captures how problems are actually solved—and ensures future reasoning follows proven, appropriate paths.**
