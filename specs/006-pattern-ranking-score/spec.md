# Feature 006-Pattern-Ranking: Score Extracted Patterns

---

## 📚 Reference Documentation

**Prerequisites**: [Feature 005: Pattern Extraction](../005-pattern-extraction-discover/) — Requires extracted patterns

**See Also:**

- [Build Plan](../../docs/architecture/build-plan.md) — Phase 3 context (ranking + optimization)
- [System Architecture](../../docs/architecture/system-architecture.md) — Ranking in learn plane
- [Pattern Detection & Pipeline](../../docs/reference/pattern-detection-and-pipeline.md) — Scoring algorithms + similarity
- **Feeds into**: Feature 008 (Optimization Loop)

## Feature Overview

Score and rank extracted reasoning patterns by effectiveness, safety, and relevance to enable intelligent pattern recommendations and feedback-driven optimization.

## User Stories

### P1: Effectiveness Scoring

**As a** system architect  
**I want to** score patterns by their effectiveness (success rate, outcome quality, user satisfaction)  
**So that** high-impact patterns are prioritized and recommended to users

**Acceptance Criteria**:

- Effectiveness score calculated from: success_rate (0-1), average_outcome_quality (0-10), user_satisfaction (0-5)
- Weighted formula: (success_rate × 0.4) + (outcome_quality / 10 × 0.35) + (user_satisfaction / 5 × 0.25)
- Score range: 0-1, updated on each feedback event
- Pattern ranked by effectiveness ascending (highest first)
- Calculate with min 5 feedback events (statistical significance)

### P1: Safety Filtering

**As a** risk officer  
**I want to** filter patterns by danger scores (integrate Phase 2.1 danger classifier output)  
**So that** high-danger patterns are flagged or excluded from recommendations

**Acceptance Criteria**:

- Integrate DangerScore from Phase 2.1 output
- Patterns with ANY "CRITICAL" danger type: flagged (not recommended)
- Patterns with ALL "MEDIUM" danger types: recommended with warning
- Patterns with only "LOW": recommended without flag
- Pattern includes danger_context (why flagged if applicable)

### P1: FSM Context Integration

**As a** reasoning engine  
**I want to** weight pattern rankings by FSM context (from Phase 2.2)  
**So that** patterns relevant to current FSM state are ranked higher

**Acceptance Criteria**:

- Integrate FSM type from Phase 2.2 (routing classification)
- Add relevance_score: pattern_target_fsm_types ∩ current_fsm_types / |current_fsm_types|
- Adjust ranking weight: effectiveness × (0.6 + 0.4 × relevance_score)
- Store pattern→fsm_type relationship (many-to-many)

### P1: Cost-Based Ranking

**As a** performance engineer  
**I want to** factor computational cost into pattern rankings  
**So that** efficient patterns are preferred during latency-sensitive operations

**Acceptance Criteria**:

- Measure execution_cost: avg latency (ms) + memory_peak (MB) / 1000 + error_rate (0-1) × 100
- Cost score: 1 / (1 + execution_cost) (inverse sigmoid, 0-1 range)
- Multi-rank formula: effectiveness × 0.4 + safety × 0.3 + cost × 0.3
- Latency target <100ms for ranking 1M patterns

### P2: Domain Matching

**As a** domain expert  
**I want to** match patterns to specific problem domains (e.g., ML, finance, legal)  
**So that** domain-relevant patterns are prioritized based on problem context

**Acceptance Criteria**:

- Domain tags: ["ml", "finance", "legal", "healthcare", "general"]
- Patterns derived from traces tagged with domain metadata
- Domain_match_score: problem_tags ∩ pattern_tags / |pattern_tags|
- Include in secondary ranking if domain context provided

## Functional Requirements

1. **Pattern Scoring Engine**
   - Calculate effectiveness, safety, relevance, cost scores (0-1 range)
   - Multi-objective ranking formula with weighted combination
   - Real-time score updates on new feedback events

2. **Danger Integration (Phase 2.1 Contract)**
   - Consume DangerScore outputs from danger classifier
   - Map danger types → pattern safety flag (CRITICAL, MEDIUM, LOW, SAFE)
   - Escalation: CRITICAL risks trigger alerts

3. **FSM Integration (Phase 2.2 Contract)**
   - Consume FSM classification + confidence scores
   - Calculate pattern relevance to FSM types
   - Weight ranking by FSM context relevance

4. **Feedback Aggregation**
   - Consume feedback events: success, outcome_quality, user_satisfaction, latency, memory
   - Aggregate with time decay (recent feedback weighted higher)
   - Min 5 events for statistical significance before ranking

5. **Batch Ranking API**
   - Input: List of patterns (with metadata), context (fsm_type, domain, danger_scores)
   - Output: Ranked list (effectiveness_score, safety_flag, relevance_score, final_rank)
   - Latency: <30ms for 1000 patterns, <100ms for 1M

6. **Pattern Persistence**
   - Store pattern→fsm_type mappings in knowledge graph
   - Persist ranking scores with timestamp
   - Enable historical score tracking

## Non-Functional Requirements

1. **Performance**
   - Rank 1M patterns in <100ms
   - Calculate all scores in <30ms for 1000 patterns
   - Batch API response: <50ms (p95)

2. **Consistency**
   - Deterministic ranking (same input → same output)
   - Version scores with timestamp
   - Atomic updates (all scores update or none)

3. **Reliability**
   - Graceful degradation: if danger/FSM data unavailable, use effectiveness only
   - Circular dependency prevention (rank by effectiveness first, inject context)
   - Error recovery: fallback to previous scores if calculation fails

4. **Compliance**
   - CRITICAL danger patterns logged (for audit trail)
   - Ranking decisions explainable (show score breakdown)
   - No sensitive data in pattern metadata

5. **Scalability**
   - Pattern storage: 1M+ patterns in Neo4j
   - Score storage: immutable score history (time-series)
   - Query efficiency: index by effectiveness_score, fsm_type, created_date

## Success Criteria

1. ✅ Effectiveness scoring: 95%+ accuracy against human raters (blind comparison)
2. ✅ Safety filtering: 100% catch rate for CRITICAL danger patterns
3. ✅ FSM relevance: 80%+ patterns correctly matched to FSM domains
4. ✅ Ranking latency: <30ms for 1000 patterns, <100ms for 1M
5. ✅ Cost-aware ranking: 30% latency reduction vs. effectiveness-only ranking
6. ✅ Feedback incorporation: Score changes within 2 feedback events

## Dependencies

- **Phase 1**: Pattern extraction output (Pattern, PatternMatch models)
- **Phase 2.1**: Danger classifier output (DangerScore contract)
- **Phase 2.2**: FSM router output (FSMClassification contract)
- **Phase 3.1**: Extracted patterns with metadata + similarity scores

## Out of Scope

- LLM-based pattern interpretation (Phase 3.4 future work)
- Real-time streaming feedback (buffered batch processing only)
- Pattern recommendation UI (Phase 4)
- Multi-user pattern collaboration (Phase 5)

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
