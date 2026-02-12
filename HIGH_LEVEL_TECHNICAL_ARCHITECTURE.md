---

# High-Level Technical Architecture (Boxes + Flows)

```
┌──────────────────────────────────────────────────────────┐
│                  INPUT SOURCES                           │
│                                                          │
│  • HuggingFace reasoning datasets                        │
│  • Agent / tool logs                                     │
│  • User problem statements                               │
│  • Existing conversation traces                          │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│            INGESTION & CANONICALIZATION                  │
│                                                          │
│  • Parse raw traces                                      │
│  • Normalize into canonical schema                       │
│    (Trace, Step, Artifact, Edge)                         │
│  • Assign IDs, timestamps, provenance                    │
└───────────────┬──────────────────────────────────────────┘
                │
        ┌───────┴─────────┐
        ▼                 ▼
┌──────────────────┐  ┌──────────────────┐
│   GRAPH STORE    │  │   VECTOR STORE   │
│   (Neo4j)        │  │   (Qdrant)       │
│                  │  │                  │
│  • Steps         │  │  • Step vectors  │
│  • Edges         │  │  • Window vectors│
│  • Artifacts     │  │  • Pattern vecs  │
│  • Patterns      │  │                  │
│                  │  │  Filterable by   │
│  Traversal &     │  │  FSM, danger,    │
│  constraints     │  │  domain          │
└─────────┬────────┘  └─────────┬────────┘
          │                      │
          └──────────┬───────────┘
                     ▼
┌──────────────────────────────────────────────────────────┐
│          ROUTING & CONTROL PLANE                         │
│                                                          │
│  1) Danger Archetype Classifier                          │
│     • Ambiguity                                          │
│     • Adversarial                                        │
│     • Irreversibility                                    │
│     • Institutional                                      │
│                                                          │
│  2) FSM Router                                           │
│     • Selects one of ~10 universal FSMs                  │
│                                                          │
│  3) Transition Guards                                    │
│     • Block unsafe execute/decide steps                  │
│     • Insert clarification / verification gates          │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│            PATTERN MINING & LIBRARY                      │
│                                                          │
│  • FSM subpath mining                                    │
│  • Graph motif mining                                    │
│  • Semantic clustering (step windows)                    │
│                                                          │
│  → Meta-thought Patterns                                 │
│    (templates + applicability + quality metrics)         │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│          NEXT-STEP RECOMMENDER                           │
│                                                          │
│  Input:                                                  │
│   • Current FSM + state                                  │
│   • Danger context                                       │
│   • Graph context                                        │
│                                                          │
│  Actions:                                                │
│   • Retrieve candidate patterns                          │
│   • Filter by FSM + danger + domain                      │
│   • Rank by success proxies                              │
│                                                          │
│  Output:                                                 │
│   • Clarifying questions                                 │
│   • Verification steps                                   │
│   • Procedural plan templates                            │
│   • Or explicit refusal/escalation                       │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│            LOGGING, EVALUATION, LEARNING                 │
│                                                          │
│  • Log pattern usage                                     │
│  • Track success proxies                                 │
│  • Human / LLM evaluation                                │
│  • Pattern pruning & refinement                          │
│  • Threshold & router updates                            │
└──────────────────────────────────────────────────────────┘
```
