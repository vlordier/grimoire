# Grimoire — Project Specification

> **See also:** [Product Requirements Document](prd.md) · [Executive Summary](prd-executive.md) · [System Architecture](../architecture/system-architecture.md) · [Problem Archetypes](../domain/problem-archetypes.md) · [Canonical Schemas](../reference/canonical-schemas.md)

---

In simple terms:

Grimoire builds a system where an AI does not solve every problem from scratch.

Instead, it:

1. **Remembers how it solved similar problems before.**
2. **Reuses good solution patterns ("recipes").**
3. **Improves those recipes over time.**
4. **Shares the best ones across users safely.**

---

## The Core Idea

The system functions as a **living cookbook for problem solving**.

* A *recipe* is not a full solution.
* It is a structured way of thinking:

  * what to check first
  * what variables to define
  * what strategy to use
  * what common mistakes to avoid
  * when to switch approaches

Over time, the system builds a large library of these reusable patterns.

---

## How It Works (Step by Step)

### 1. A new problem comes in

The AI:

* Summarizes what the problem really is.
* Extracts constraints (time limit? tools available? domain?).

This creates a clean "problem signature".

---

### 2. It looks up a good starting recipe

Instead of reasoning from scratch, the system asks:

> "Has a similar problem been solved before?"

It retrieves:

* The best matching recipe.
* A couple of alternatives just in case.

This is **exploitation** — reuse what already works.

---

### 3. It executes the recipe carefully

It runs through the structured steps:

* check assumptions
* apply method
* verify output
* handle known failure modes

This is done step-by-step (via sequential thinking).

If something fails:

* It can hop to an alternate recipe.
* It can try a fallback branch.

This is **controlled exploration**.

---

### 4. It verifies the result

Before declaring success:

* It checks correctness (tests, math substitution, validation).
* It logs what happened.

This is crucial — otherwise it would just learn from hallucinations.

---

### 5. It learns from the outcome

If the recipe worked:

* It strengthens confidence in that pattern.

If it failed:

* It tries to understand why.
* Maybe the recipe was missing a check.
* Maybe it needed a fallback.
* Maybe the retrieval was wrong.

It proposes improvements.

Critically, those improvements are **not immediately shared with all users**.

---

## The Federated Part

Many users run this system locally.

Each user:

* Solves problems.
* Generates traces (evidence of what worked).
* Proposes improvements.

All of this goes to a shared server.

The server:

* Filters noise.
* Tests proposed improvements.
* Verifies them on challenge cases.
* Promotes only the good ones.

This keeps the shared memory high-quality.

---

## Exploration vs Exploitation

Both are needed:

* **Exploitation** = reuse proven recipes to solve problems cheaply and reliably.
* **Exploration** = when something breaks, try variations and discover better patterns.

The system balances them:

* Start with exploitation.
* Explore only when needed.
* Keep what proves robust.
* Discard what doesn't.

---

## System Layers

| Layer               | Purpose                                 |
| ------------------- | --------------------------------------- |
| Canonical schema    | One format for all reasoning traces     |
| Graph store (Neo4j) | Structure: steps, edges, artifacts      |
| Vector store (Qdrant)| Semantics: similar steps/patterns      |
| Danger router       | Detect high-risk problems early         |
| FSM engine          | Enforce disciplined reasoning           |
| Pattern library     | Reusable "meta-thoughts"                |
| Recommender         | Suggest next step from best patterns    |
| Evaluation loop     | Track what works, prune what doesn't    |
| Federated layer     | Share safely across users               |

> **Note:** The federated layer is a long-term goal. No technical design exists yet. See the [Build Plan](../architecture/build-plan.md) for the current phased roadmap, which focuses on the single-instance system first.

---

## The Long-Term Outcome

The long-term outcome is a system that:

* Starts from proven procedures.
* Adapts when needed.
* Improves automatically.
* Maintains safety invariants.

All of this operates **transparently and auditably**.
