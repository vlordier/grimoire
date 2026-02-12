# Implementation Plan: FSM Router

**Phase**: 2.2  
**Feature Branch**: `003-fsm-router-classify`  
**Status**: Planning Phase Complete  
**Effort Estimate**: 4-6 days (~1 week)

---

## Overview

The FSM Router selects 1 of 10 universal FSM types based on problem intent and context. It enables the system to adapt its reasoning strategy to the problem structure (is this a debugging task? A design problem? An optimization? etc.).

### Key Data Flow

```
Input: Problem Text
         ↓
    FSM Router
         ↓
    Feature Extraction (keywords, problem type)
         ↓
    Pattern Matching (problem → FSM archetype)
         ↓
    Selection + Confidence Scoring
         ↓
Output: FSM Type + Confidence [0, 1]
```

---

## Phase 0: Research & Clarification

### Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| **Routing Algorithm** | Keyword matching vs LLM classifier | Keyword matching (v1) | Fast, deterministic, no cost. LLM in v2. |
| **FSM Coverage** | All 10 vs subset | All 10 (reference impl) | Reference impl has patterns for all 10. |
| **Confidence Scoring** | Keyword coverage % vs semantic similarity | Keyword coverage % | Simple, interpretable, no embedding cost. |
| **Fallback Strategy** | Default FSM vs rejection | Default FSM (clarify_frame) | Always recommend something; user can override. |
| **Learning** | Static patterns vs feedback loop | Static v1 | Patterns tuned by team. Feedback loop in Phase 3. |
| **Multi-FSM Problems** | Primary + secondary vs single | Primary + confidence | Return 1 FSM; confidence indicates certainty. |

### Key Questions

**Q1: What's the minimum confidence threshold to recommend an FSM?**
- A: 0.5 (>50% keyword match). Below 0.5, default to clarify_frame.

**Q2: How do we handle ambiguous problems (e.g., "Make the system better")?**
- A: Lowest confidence, default to clarify_frame (which narrows scope first).

**Q3: Can a problem match multiple FSMs equally well?**
- A: Yes. Return best match; second-best available in response metadata for context.

**Q4: Should FSM selection depend on Danger classification (002)?**
- A: Not hard dependency. Can work independently. Phase 3 optimization: use danger scores to refine FSM.

**Q5: How do we extend keywords/patterns for new domains?**
- A: Config-driven keyword lists in routing_config.yaml. Easy to add without code change.

---

## Phase 1: Data Models

### Input Models

```python
FSMRouterRequest(
    problem_text: str,              # "Debug why async tasks are timing out"
    context: Optional[Dict],        # domain, user_level, prior_fsm_id
    optional_fsm_hints: Optional[List[str]]  # ["diagnose", "debug"] - user hint
)
```

### Output Models

```python
FSMRoute(
    selected_fsm_id: str,           # "fsm_diagnose_fix"
    selected_fsm_name: str,         # "Diagnose & Fix" (readable name)
    confidence: float,              # [0, 1] - how confident we are
    reasoning: str,                 # "Keyword: bug, timeout, root cause matched diagnose_fix"
    alternative_fsms: List[Dict],   # [{fsm_id, confidence, keywords_matched}]
    computed_at: datetime,
    router_version: str
)

FSMRouterResponse(
    trace_id: str,
    route: FSMRoute,
    routing_ms: int
)
```

### Enum: FSMType

```python
class FSMType(str, Enum):
    CLARIFY_FRAME = "fsm_clarify_frame"           # Narrow scope, define success
    DIAGNOSE_FIX = "fsm_diagnose_fix"             # Find root cause, fix, verify
    DESIGN_DECIDE = "fsm_design_decide"           # Explore options, decide
    OPTIMIZE = "fsm_optimize"                     # Tune parameters
    VERIFY = "fsm_verify"                         # Test hypothesis
    TRANSFORM = "fsm_transform"                   # Reshape problem
    OPERATE_HARDEN = "fsm_operate_harden"         # Stabilize system
    POSTMORTEM = "fsm_postmortem"                 # Analyze failure
    RESOLVE_CONFLICT = "fsm_resolve_conflict"     # Negotiate constraints
    ADVERSARIAL_LOOP = "fsm_adversarial_loop"     # Anticipate attacks
```

### Keyword Configuration

```python
RoutingConfig(
    fsm_keyword_patterns: Dict[str, List[str]],  # FSM ID → keyword list
    confidence_threshold: float,                  # 0.5
    default_fsm: str,                             # "fsm_clarify_frame"
    keyword_weights: Dict[str, float]             # optional per-keyword boost
)

# Example patterns (from reference impl)
{
    "fsm_diagnose_fix": [
        "bug", "debug", "error", "fix", "root cause",
        "why", "not working", "broken", "fail"
    ],
    "fsm_design_decide": [
        "design", "architect", "choose", "option", "alternative",
        "build", "create", "which", "compare"
    ],
    "fsm_optimize": [
        "performance", "speed", "optimize", "faster", "efficient",
        "improve", "tune", "slow", "latency"
    ],
    ...
}
```

---

## Phase 2: Implementation

### Module Structure

```
grimoire_fsm/
├── router.py
│   ├── FSMRouter (main class)
│   ├── route(problem_text, context) → FSMRoute
│   └── extract_features(text) → List[keyword_matches]
├── patterns.py
│   ├── KEYWORD_PATTERNS (dict)
│   └── confidence_to_nearest_fsm(keywords) → (fsm_id, score)
├── config/
│   └── routing_config.yaml
└── tests/
    ├── test_keyword_extraction.py
    ├── test_fsm_routing.py
    └── test_e2e_routing.py
```

### Key Algorithms

**1. Keyword Extraction**

```python
def extract_keywords(text: str) -> Dict[str, int]:
    """Count occurrences of FSM keywords in problem text."""
    keywords_matched = defaultdict(int)
    text_lower = text.lower()
    
    for fsm_id, keywords in KEYWORD_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                keywords_matched[fsm_id] += 1
    
    return keywords_matched
```

**2. Confidence Scoring**

```python
def score_fsm(keywords_matched: int, total_keywords_possible: int) -> float:
    """Score FSM as percentage of matched keywords."""
    if total_keywords_possible == 0:
        return 0.0
    confidence = keywords_matched / total_keywords_possible
    return min(confidence, 1.0)  # Cap at 1.0
```

**3. FSM Selection**

```python
def select_fsm(problem_text: str, config: RoutingConfig) -> FSMRoute:
    keywords = extract_keywords(problem_text)
    
    scores = {
        fsm_id: score_fsm(count, len(patterns))
        for fsm_id, count in keywords.items()
        for patterns in [KEYWORD_PATTERNS[fsm_id]]
    }
    
    best_fsm = max(scores, key=scores.get, default=config.default_fsm)
    confidence = scores.get(best_fsm, 0.0)
    
    if confidence < config.confidence_threshold:
        best_fsm = config.default_fsm
        confidence = 0.0  # Indicates default fallback
    
    return FSMRoute(
        selected_fsm_id=best_fsm,
        confidence=confidence,
        reasoning=f"Keywords matched: {keywords.get(best_fsm, [])}",
        alternative_fsms=[...]
    )
```

### API Endpoints

```
POST /v1/route
  Request: FSMRouterRequest
  Response: FSMRouterResponse

GET /v1/routing/config
  Response: RoutingConfig
  
PUT /v1/routing/config
  Request: RoutingConfigUpdate
  Response: RoutingConfig (updated)
```

### Integration Points

- **Input**: Problem text (from Phase 1 TraceBundle.problem)
- **Output**: FSM type selection → used by Step creation
- **Optional**: Danger scores (from 002) can refine confidence in Phase 3

### Neo4j Cypher Templates

**Store FSM Classification on Step**
```cypher
// Attach FSM classification to Step node
MATCH (s:Step {step_id: $step_id})
SET s.fsm_type = $fsm_type,
    s.fsm_confidence = $confidence,
    s.fsm_computed_at = datetime(),
    s.fsm_router_version = $version
RETURN s.step_id, s.fsm_type, s.fsm_confidence
```

**Query Steps by FSM Type**
```cypher
// Find all steps of a specific FSM type
MATCH (t:Trace)-[:CONTAINS]->(s:Step)
WHERE s.fsm_type = $fsm_type
  AND s.fsm_confidence >= 0.7
RETURN t.trace_id, s.step_id, s.content[0..100] as preview
ORDER BY s.fsm_computed_at DESC
LIMIT 100
```

**Aggregate FSM Distribution**
```cypher
// Distribution of FSM types across traces
MATCH (s:Step)
WHERE s.fsm_type IS NOT NULL
RETURN s.fsm_type as fsm,
       count(*) as count,
       avg(s.fsm_confidence) as avg_confidence
ORDER BY count DESC
```

**Find Traces by FSM Type for Pattern Extraction**
```cypher
// Get complete traces of specific FSM type (for Phase 3.1)
MATCH (t:Trace)-[:CONTAINS]->(s:Step)
WHERE s.fsm_type = $fsm_type
  AND s.step_number = 0  // First step has FSM classification
WITH t
MATCH (t)-[:CONTAINS]->(all_steps:Step)
RETURN t.trace_id,
       collect(all_steps {.*}) as steps
ORDER BY t.created_at DESC
LIMIT 1000
```

### Hot-Reload Configuration

```python
import asyncio
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloader(FileSystemEventHandler):
    """Hot-reload routing configuration."""
    
    def __init__(self, config_path: str, router: FSMRouter):
        self.config_path = config_path
        self.router = router
        self.last_reload = 0
    
    def on_modified(self, event):
        if event.src_path == self.config_path:
            # Debounce: wait 500ms after last change
            current_time = time.time()
            if current_time - self.last_reload > 0.5:
                self.last_reload = current_time
                asyncio.create_task(self.reload_config())
    
    async def reload_config(self):
        """Reload configuration without restart."""
        try:
            async with aiofiles.open(self.config_path, 'r') as f:
                content = await f.read()
            
            new_config = yaml.safe_load(content)
            self.router.update_config(RoutingConfig(**new_config))
            
            logger.info(f"Reloaded routing config: {len(new_config['fsm_keyword_patterns'])} FSMs")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")

# Setup file watcher
def setup_hot_reload(config_path: str, router: FSMRouter):
    """Set up file watcher for hot reload."""
    observer = Observer()
    handler = ConfigReloader(config_path, router)
    observer.schedule(handler, path=os.path.dirname(config_path), recursive=False)
    observer.start()
    return observer

# API endpoint for manual reload
@app.post("/v1/config/reload")
async def reload_config():
    """Manually trigger configuration reload."""
    try:
        router.load_config()
        return {
            "status": "reloaded",
            "fsm_count": len(router.config.fsm_keyword_patterns),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Conflict Resolution

```python
def resolve_tie(scores: Dict[str, float], keywords_matched: Dict[str, List[str]]) -> str:
    """
    Resolve ties when multiple FSMs have same confidence.
    Priority:
    1. Most keywords matched (specificity)
    2. FSM priority order (diagnose > design > optimize > ...)
    3. Random (deterministic hash of problem text)
    """
    max_score = max(scores.values())
    tied_fsms = [fsm for fsm, score in scores.items() if score == max_score]
    
    if len(tied_fsms) == 1:
        return tied_fsms[0]
    
    # 1. Most specific (most keywords)
    keyword_counts = {
        fsm: len(keywords_matched.get(fsm, [])) 
        for fsm in tied_fsms
    }
    max_keywords = max(keyword_counts.values())
    most_specific = [fsm for fsm, count in keyword_counts.items() 
                     if count == max_keywords]
    
    if len(most_specific) == 1:
        return most_specific[0]
    
    # 2. Priority order
    FSM_PRIORITY = [
        "fsm_diagnose_fix",
        "fsm_design_decide",
        "fsm_optimize",
        "fsm_verify",
        "fsm_transform",
        "fsm_clarify_frame"
    ]
    
    for priority_fsm in FSM_PRIORITY:
        if priority_fsm in most_specific:
            return priority_fsm
    
    # 3. Deterministic fallback
    return most_specific[0]
```

---

## Phase 3: Testing

### Unit Tests

```python
def test_keyword_extraction():
    text = "Debug why the async task times out"
    keywords = extract_keywords(text)
    assert keywords["fsm_diagnose_fix"] > 0
    
def test_clarity_problem_defaults_to_clarify_frame():
    text = "Do something good"  # Vague
    route = router.route(text)
    assert route.selected_fsm_id == "fsm_clarify_frame"
    assert route.confidence == 0.0  # Below threshold
    
def test_design_problem_routes_to_design_decide():
    text = "Architect a new database schema"
    route = router.route(text)
    assert route.selected_fsm_id == "fsm_design_decide"
    assert route.confidence >= 0.5
```

### Integration Tests

```python
def test_fsm_routing_with_phase1_traces():
    # Load 50 traces from Phase 1 ingestion
    # Route each
    # Verify:
    # - 90%+ get routed (not defaulted)
    # - Routing correlates with problem domain
    # - Performance < 100ms per trace
    
def test_fsm_selection_consistency():
    # Same problem routed twice = same FSM
    # Verify deterministic (no randomness)
```

### Evaluation Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Coverage | 90%+ non-default routing | % of problems above confidence threshold |
| Accuracy | 80%+ human agreement | Expert review on 20 representative problems |
| Performance | < 100ms per route | Batch 1000, measure P50/P99 |
| Keywords | Comprehensive | All 10 FSMs have 5+ relevant keywords |

---

## Phase 4: Deployment & Rollout

### Steps

1. **Week 1-2**: Implementation (code + tests)
2. **Week 2**: Integration with Phase 1 ingestion pipeline
3. **Week 3**: Evaluation on historical traces
4. **Week 4**: Tuning keyword weights based on feedback
5. **End**: Ready for Phase 2.3 (Guards) to consume FSM selection

### Handoff to Phase 3

Once 003 is complete:
- FSM Router API available
- Can be called to select FSM for any reasoning trace
- Confidence scores help Phase 3 identify uncertain cases for human review

---

## Success Criteria

- [ ] All 10 FSM types routable (90%+ confidence for obvious problems)
- [ ] Keyword patterns comprehensive (cover common problem phrasings)
- [ ] Performance < 100ms per route
- [ ] Integration with Phase 1: traces ingested → routed to FSM
- [ ] 80%+ human agreement on 20-problem evaluation set
- [ ] Config file (routing_config.yaml) easy to update without code change

---

## Dependencies

- ✅ Independent from Danger Classifier (002)
- ✅ Can start in parallel with 002 or after 002 complete
- ⚠️ Must complete before Phase 2.3 (Transition Guards) which depends on FSM state

---

## Effort Breakdown

| Phase | Task | Days | Notes |
|-------|------|------|-------|
| 0 | Research + design decisions | 1 | Clarify keyword coverage, confidence thresholds |
| 1 | Data models + config schema | 0.5 | Pydantic v2, RoutingConfig enum |
| 2 | Router implementation | 2 | Keyword extraction, scoring, selection, API |
| 3 | Tests (unit + integration) | 1 | 20+ test cases, evaluation metrics |
| 4 | Integration + tuning | 0.5 | Connect to Phase 1, calibrate thresholds on real data |
| **Total** | | **4-6 days** | Ranges based on keyword tuning iterations |

---

## See Also

- [spec.md](spec.md) — User stories, requirements
- [data-model.md](data-model.md) — Pydantic v2 schemas
- [contracts/fsm-router-api.md](contracts/fsm-router-api.md) — API contract + examples
- [docs/domain/fsm-catalogue.md](../../docs/domain/fsm-catalogue.md) — FSM types & state machines
- [Reference Impl](../../docs/reference/fsm-router-impl.md) — Working code skeleton (if available)
