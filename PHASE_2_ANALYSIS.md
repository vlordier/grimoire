# Phase 2 Roadmap — Detailed Analysis

**Date**: 12 February 2026  
**Current State**: Phase 1 ✅ Complete (Schemas + Ingestion ready)  
**Next Phase**: Phase 2 (Control Plane — Routing & Safety Gates)

---

## Architecture Overview

Phase 2 builds the **control plane** that ensures safe reasoning by:

1. Classifying danger archetypes in problems (ambiguity, adversarial, irreversibility, institutional)
2. Selecting appropriate reasoning FSM (diagnose vs design vs optimize vs verify, etc.)
3. Enforcing transition guards (block premature actions, require verification, escalate institutional risks)

### Data Flow

```text
Input Problem
     ↓
[002] Danger Classifier ──→ Danger scores (0-1 for each archetype)
     ↓
[003] FSM Router ──→ Selected FSM (1 of 10)
     ↓
[004] Transition Guards ──→ Allow/Block/Escalate decisions
     ↓
Output: Safe, procedurally-guided next step recommendation
```

---

## Component Analysis

### 2.1: Danger Classifier (002) — START HERE ✅

**Purpose**: Identify 4 danger archetypes in reasoning traces and score them [0, 1]

**Reference Implementation**: Exists at [docs/reference/danger-classification-impl.md](docs/reference/danger-classification-impl.md)

#### What's Already Done

- ✅ Design rationale documented
- ✅ Pydantic v2 reference code (~500 lines)
- ✅ Regex patterns for keyword detection (ASSERT, ASK, BRANCH, EXECUTE, etc.)
- ✅ Guard logic (no execute while ambiguous, no irreversible without verification, etc.)
- ✅ Unit test examples (pytest)

#### What Needs to be Built

1. **Feature Spec** (002-danger-router)
   - User stories: "As a safety engineer, I want..."
   - Requirements: Input shape, output shape, accuracy targets
   - Risk analysis: What happens if classifier fails?

2. **API Contract** (danger-classifier-api.md)
   - `DangerClassifierRequest`: trace text, context, config
   - `DangerClassifierResponse`: 4 danger scores + evidence spans
   - `classify_trace()` function signature
   - Error handling (invalid input, null checks)

3. **Data Model** (extended enums/types)
   - `DangerType` enum (already in canonical, use it)
   - `DangerEvidence` (evidence spans, keyword matches)
   - `DangerContext` (optional context for scoring)

4. **Implementation Tests**
   - Unit tests: regex patterns, scoring logic
   - Integration tests: pipeline with Phase 1 ingestion
   - Edge cases: empty text, mixed signals, adversarial examples

#### Complexity: **MEDIUM** ⚠️

**Why Medium?**

- Regex logic is straightforward, but tuning thresholds is tricky
- Balancing false positives vs false negatives in scoring
- Phase 2 depends on this classifier being reasonably accurate
- No LLM calls needed in v1 (reference impl uses rules only)

#### Dependencies: NONE

- ✅ Can start immediately
- Works standalone from FSM Router
- No data dependencies

#### Effort Estimate

- **Planning** (spec + clarification): 2-3 days
- **Implementation** (contracts + tests): 3-4 days
- **Validation** (integration with Phase 1): 1 day
- **Total**: ~6-8 days

#### Success Criteria

- [ ] Classifier correctly identifies all 4 danger types in examples
- [ ] Scores correlate with human judgment (e.g., ambiguous problems → high ambiguity score)
- [ ] All guard conditions in reference impl work as specified
- [ ] Phase 1 ingestion pipeline can call classifier on stored traces

---

### 2.2: FSM Router (003) — INDEPENDENT, CAN START IN PARALLEL

**Purpose**: Select 1 of 10 universal FSMs based on problem intent

**10 FSM Types** (from [docs/domain/fsm-catalogue.md](docs/domain/fsm-catalogue.md)):

1. `fsm_clarify_frame` — Narrow scope, define success metrics
2. `fsm_diagnose_fix` — Find root cause, apply fix, verify
3. `fsm_design_decide` — Explore options, decide, commit
4. `fsm_optimize` — Tune parameters, measure, repeat
5. `fsm_verify` — Test hypothesis, check all paths
6. `fsm_transform` — Reshape problem structure
7. `fsm_operate_harden` — Stabilize system, prepare for production
8. `fsm_postmortem` — Analyze failure, extract lessons
9. `fsm_resolve_conflict` — Negotiate constraints, find consensus
10. `fsm_adversarial_loop` — Anticipate attacks, strengthen defense

#### What Exists

- ✅ FSM catalogue with state machines, transitions, guards
- ✅ Problem archetypes linked to FSMs (debugging → diagnose_fix, design problem → design_decide)
- ✅ Selection heuristics (keyword matching to FSM types)

#### What Needs to be Built

1. **Feature Spec** (003-fsm-router)
   - User stories: "As a developer, I want FSM type to be auto-selected from problem..."
   - Requirements: Mapping from problem intent → FSM

2. **API Contract** (fsm-router-api.md)
   - `FSMRouterRequest`: problem_text, optional_hints, domain
   - `FSMRouterResponse`: selected_fsm_id, confidence, reasoning
   - `route_problem()` function
   - Fallback: default FSM if confidence too low

3. **Routing Algorithm** (v1 can be rule-based)
   - Pattern matching: "debug" → diagnose_fix, "design" → design_decide
   - Keyword extraction: problem verb → FSM type
   - Optional LLM classifier for ambiguous cases

4. **Tests**
   - Unit: keyword extraction, mapping rules
   - Integration: e2e from problem text → FSM selection

#### Complexity: **MEDIUM** ⚠️

**Why Medium?**

- Keyword matching is simple, but coverage needs to be comprehensive
- Some problems span multiple FSMs (need fallback/secondary)
- Confidence scoring is subjective
- Future upgrade to LLM classifier needed

#### Dependencies: NONE

- ✅ Completely independent from Danger Classifier
- Danger Classifier & FSM Router can work in parallel

#### Effort Estimate

- **Planning** (spec): 1-2 days
- **Implementation** (contract + keyword mapping): 2-3 days
- **Validation**: 1 day
- **Total**: ~4-6 days

#### Success Criteria

- [ ] Correctly routes 90%+ of common problem types
- [ ] Handles edge cases (multi-FSM problems)  
- [ ] Integrates with Phase 1 problem classification

---

### 2.3: Transition Guards (004) — START AFTER 002 & 003

**Purpose**: Enforce safety gates during FSM state transitions based on danger + FSM state

**4 Guards** (from reference impl):

1. **NO_EXECUTE_AMBIGUOUS** — Block "execute" while ambiguity > threshold
2. **NO_IRREVERSIBLE_UNVERIFIED** — Block irreversible actions without verification step
3. **ADVERSARIAL_REQUIRES_MONITORING** — Adversarial problems require monitoring closure  
4. **INSTITUTIONAL_REQUIRES_STAKEHOLDERS** — Institutional risks need stakeholder sign-off

#### What Exists

- ✅ Guard logic implemented in danger-classification-impl.md
- ✅ State machine transition points identified
- ✅ Examples showing how guards block/allow steps

#### What Needs to be Built

1. **Feature Spec** (004-transition-guards)
   - User stories: "As a risk manager, I want unsafe transitions to be blocked..."

2. **API Contract** (guard-api.md)
   - `TransitionGuardRequest`: current_fsm_state, proposed_step_type, danger_scores, context
   - `TransitionGuardResponse`: allowed (bool), reason, escalation_path (if blocked)
   - `check_transition()` function

3. **Guard Logic**
   - Each guard reads danger_scores (from 002) + FSM state (from 003)
   - Returns decision: ALLOW / BLOCK / ESCALATE

4. **Integration**
   - Guards called during Step creation
   - Blocked transitions stored as `Step.guard_blocked` metadata
   - Escalations created as `Step.escalation_path` edges

#### Complexity: **LOW** ✅

**Why Low?**

- Most logic already exists
- Mainly about composing danger scores + FSM state into decisions
- No new concepts, just orchestration

#### Dependencies: BOTH 002 & 003

- ❌ Cannot start until Danger Classifier planned
- ❌ Cannot start until FSM Router planned
- ✅ Can be implemented once both are understood

#### Effort Estimate

- **Planning** (spec): 1 day (mostly done)
- **Implementation** (contract + logic): 2 days
- **Validation**: 1 day
- **Total**: ~4 days

#### Success Criteria

- [ ] All 4 guards work as specified
- [ ] Blocked transitions clearly logged with reason
- [ ] Escalation paths created correctly

---

## Recommended Sequence

### Timeline Option A: Sequential (Safe, Can Ship Each)

```text
Week 1:
  Mon-Tue:   002 Planning (spec.md, research.md, plan.md)
  Wed-Thu:   002 Implementation (API contract, code, tests)
  Fri:       002 Validation + merge to main

Week 2:
  Mon-Tue:   003 Planning
  Wed-Thu:   003 Implementation
  Fri:       003 Validation + merge

Week 3:
  Mon-Tue:   004 Planning
  Wed-Thu:   004 Implementation
  Fri:       004 Validation + merge + ship Phase 2 complete

Total: ~16 days (3 weeks)
```

### Timeline Option B: Parallel with Staging (Faster)

```text
Week 1:
  Mon-Tue:   002 Planning + 003 Planning (parallel)
  Wed-Thu:   002 Implementation + 003 Implementation (parallel)
  Fri:       002 + 003 Validation, merge staging branch

Week 2:
  Mon-Tue:   004 Planning (now that 002 & 003 understood)
  Wed-Thu:   004 Implementation
  Fri:       004 Validation, merge staging → main

Total: ~10-12 days (2 weeks)
```

---

## Why Start with 002 (Danger Classifier)

| Criterion | 002 | 003 | 004 |
|-----------|-----|-----|-----|
| **Reference impl exists?** | ✅ Yes, detailed | ⚠️ Partial | ✅ Yes |
| **Independent?** | ✅ Yes | ✅ Yes | ❌ No (needs 002+003) |
| **Complexity** | Medium | Medium | Low |
| **Unblocks other features?** | ✅ Unblocks 004 | ✅ Unblocks 004 | ❌ Needs both |
| **Clear success criteria?** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Documentation complete?** | ✅ Yes | ⚠️ Partial | ✅ Yes |

**Recommendation**: **Start with 002, then decide 003 vs 004**

- 002 has the most complete reference material
- 002 unblocks 004 (guard logic depends on danger scores)
- 003 can start in parallel or after 002
- 004 must wait for both, but will be fast

---

## Integration Points

### Phase 1 → Phase 2 Integration Points

- **Ingestion** (Phase 1) → **Danger Classification** (002): Classify new traces as they're ingested
- **Danger Scores** (002) → **Guards** (004): Guards read scores
- **FSM Selection** (003) → **Guards** (004): Guards read FSM state
- **Guards** (004) → **Next-Step Recommender** (Phase 3): Safe transitions available

### Input from Phase 1

- ✅ TraceBundle schema (defined)
- ✅ Step/Artifact models (defined)
- ✅ Danger score types (defined in canonical)
- ✅ Canonical FSM definition (docs/domain/fsm-catalogue.md)

### Output for Phase 3

- Step classifications + safety metadata
- FSM state assignments
- Blocked/escalated transition log
- Guard evidence (which rule blocked)

---

## Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Danger classifier under-detects real risks | **HIGH** | Reference impl has high-coverage keyword list; add threshold tuning; Phase 2 testing |
| FSM router misclassifies problems | **MEDIUM** | Can override; fallback to default FSM; add confidence score |
| Guards too strict (block too many) | **MEDIUM** | Human in the loop; can add exceptions; logs for tuning |
| Guards too permissive (miss real danger) | **HIGH** | Start conservative; audit with security team |

---

## Summary: Decision Matrix

```text
Choose 002 (Danger Classifier) if you want to:
  ✅ Start with well-documented reference code
  ✅ Unblock Guard implementation (004) quickly
  ✅ Begin with lower-risk feature (mostly rules, not ML)
  ✅ Have immediate Phase 1 integration point

Choose 003 (FSM Router) if you want to:
  ✅ Build procedural flow first
  ✅ Leave danger classification for later
  ✅ Focus on problem classification
  ✅ Can work 100% independently

Recommended: 👉 START WITH 002, then 003 in parallel/after
```

---

## Next Action

**Ready to proceed?**

1. ✅ Review this analysis
2. 👉 Confirm: Start with 002-danger-router? (Y/N)
3. Then: Create feature branch + initialize spec.md

**Or**: Want to explore 003 first? Different analysis available.
