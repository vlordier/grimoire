# Neo4j Schema Migration Guide

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: Grimoire Phases 1-3 (8 Features)  
**Database**: Neo4j 5.x

---

## Overview

This document defines the strategy for evolving the Neo4j graph schema as Grimoire features progress through development phases. Schema changes are inevitable as new features (002-008) add new node types, relationships, and properties.

**Migration Principles** (from Constitution):

- Schema versioning MUST be tracked
- Migrations MUST be explicit and reversible
- Backward compatibility MUST be maintained during transitions
- Data loss is NOT acceptable

---

## Schema Version Tracking

### Version Node

Every Neo4j database must have a singleton `SchemaVersion` node:

```cypher
// Create or update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.3.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_pattern_ranking",
    sv.previous_version = "1.2.0",
    sv.description = "Added RankScore nodes for Phase 3.2"
RETURN sv
```

### Version History

```cypher
// Track migration history
CREATE (mh:MigrationHistory {
    version: "1.3.0",
    applied_at: datetime(),
    applied_by: "migration_script_v1.3.0.cypher",
    duration_ms: 4500,
    nodes_created: 0,
    relationships_created: 0,
    properties_added: 0,
    rollback_script: "rollback_v1.3.0.cypher"
})
```

---

## Phase-by-Phase Schema Evolution

### Phase 1 (001): Foundation Schema

**Base Schema Version**: 1.0.0

```cypher
// Core nodes
(:Trace {trace_id, domain, created_at, ...})
(:Step {step_id, content, embedding_id, step_number, ...})
(:Edge {edge_id, edge_type, ...})

// Core relationships
(:Trace)-[:CONTAINS]->(:Step)
(:Step)-[:NEXT]->(:Step)
(:Step)-[:REVISES|DEPENDS_ON|...]->(:Step)
```

**Constraints**:

```cypher
CREATE CONSTRAINT trace_id_unique IF NOT EXISTS
FOR (t:Trace) REQUIRE t.trace_id IS UNIQUE;

CREATE CONSTRAINT step_id_unique IF NOT EXISTS
FOR (s:Step) REQUIRE s.step_id IS UNIQUE;

CREATE INDEX step_embedding_id_idx IF NOT EXISTS
FOR (s:Step) ON (s.embedding_id);
```

---

### Phase 2.1 (002): Danger Classification Schema

**Migration**: 1.0.0 → 1.1.0

```cypher
// Migration: v1.1.0_add_danger_scores.cypher
// Apply: After deploying 002-danger-router-classify

// Add danger score properties to Step nodes
MATCH (s:Step)
WHERE s.danger_ambiguity IS NULL
SET s.danger_ambiguity = 0.0,
    s.danger_adversarial = 0.0,
    s.danger_irreversibility = 0.0,
    s.danger_institutional = 0.0;

// Create index for danger score queries
CREATE INDEX step_danger_ambiguity_idx IF NOT EXISTS
FOR (s:Step) ON (s.danger_ambiguity);

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.1.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_danger_scores",
    sv.description = "Added danger score properties to Step nodes for Phase 2.1";
```

**Rollback**: v1.1.0_rollback.cypher

```cypher
// Remove danger score properties (data loss warning!)
MATCH (s:Step)
REMOVE s.danger_ambiguity,
       s.danger_adversarial,
       s.danger_irreversibility,
       s.danger_institutional,
       s.danger_computed_at,
       s.danger_classifier_version;

DROP INDEX step_danger_ambiguity_idx IF EXISTS;

// Restore version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.0.0";
```

---

### Phase 2.2 (003): FSM Classification Schema

**Migration**: 1.1.0 → 1.2.0

```cypher
// Migration: v1.2.0_add_fsm_classification.cypher
// Apply: After deploying 003-fsm-router-classify

// Add FSM classification properties to Step nodes
MATCH (s:Step)
WHERE s.fsm_type IS NULL
SET s.fsm_type = "unknown",
    s.fsm_confidence = 0.0;

// Create index for FSM queries
CREATE INDEX step_fsm_type_idx IF NOT EXISTS
FOR (s:Step) ON (s.fsm_type);

CREATE INDEX step_fsm_confidence_idx IF NOT EXISTS
FOR (s:Step) ON (s.fsm_confidence);

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.2.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_fsm_classification",
    sv.description = "Added FSM classification properties for Phase 2.2";
```

---

### Phase 2.3 (004): Guard Decision Schema

**Migration**: 1.2.0 → 1.3.0

```cypher
// Migration: v1.3.0_add_guard_decisions.cypher
// Apply: After deploying 004-transition-guards-enforce

// Create GuardDecision nodes (don't add to Step, separate node)
CREATE CONSTRAINT guard_decision_id_unique IF NOT EXISTS
FOR (g:GuardDecision) REQUIRE g.decision_id IS UNIQUE;

CREATE INDEX guard_decision_trace_id_idx IF NOT EXISTS
FOR (g:GuardDecision) ON (g.trace_id);

// Create relationship type
// (:Step)-[:BLOCKED_BY_GUARD]->(:GuardDecision)

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.3.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_guard_decisions",
    sv.description = "Added GuardDecision nodes for Phase 2.3";
```

---

### Phase 3.1 (005): Pattern Extraction Schema

**Migration**: 1.3.0 → 2.0.0 (MAJOR - new node types)

```cypher
// Migration: v2.0.0_add_pattern_extraction.cypher
// Apply: After deploying 005-pattern-extraction-discover

// Create Pattern node
CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (p:Pattern) REQUIRE p.pattern_id IS UNIQUE;

CREATE INDEX pattern_fsm_types_idx IF NOT EXISTS
FOR (p:Pattern) ON (p.fsm_types);

CREATE INDEX pattern_canonical_hash_idx IF NOT EXISTS
FOR (p:Pattern) ON (p.canonical_hash);

// Create PatternStep node (sub-graph structure)
CREATE CONSTRAINT pattern_step_id_unique IF NOT EXISTS
FOR (ps:PatternStep) REQUIRE ps.pattern_step_id IS UNIQUE;

// Create CostProfile node
CREATE CONSTRAINT cost_profile_id_unique IF NOT EXISTS
FOR (cp:CostProfile) REQUIRE cp.profile_id IS UNIQUE;

// Create relationships
// (:Pattern)-[:HAS_STEP {order}]->(:PatternStep)
// (:Pattern)-[:HAS_COST_PROFILE]->(:CostProfile)
// (:Pattern)-[:MATCHES_TRACE {match_score}]->(:Trace)

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "2.0.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_pattern_extraction",
    sv.description = "Added Pattern, PatternStep, CostProfile nodes for Phase 3.1";
```

---

### Phase 3.2 (006): Pattern Ranking Schema

**Migration**: 2.0.0 → 2.1.0

```cypher
// Migration: v2.1.0_add_pattern_ranking.cypher
// Apply: After deploying 006-pattern-ranking-score

// Create RankScore node (immutable ranking history)
CREATE CONSTRAINT rank_score_id_unique IF NOT EXISTS
FOR (r:RankScore) REQUIRE r.rank_score_id IS UNIQUE;

CREATE INDEX rank_score_pattern_id_idx IF NOT EXISTS
FOR (r:RankScore) ON (r.pattern_id);

CREATE INDEX rank_score_effectiveness_idx IF NOT EXISTS
FOR (r:RankScore) ON (r.effectiveness_score);

// Create relationship
// (:Pattern)-[:HAS_RANKING {version}]->(:RankScore)

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "2.1.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_pattern_ranking",
    sv.description = "Added RankScore nodes for Phase 3.2";
```

---

### Phase 3.3 (008): Optimization Loop Schema

**Migration**: 2.1.0 → 2.2.0

```cypher
// Migration: v2.2.0_add_optimization_loop.cypher
// Apply: After deploying 008-optimization-loop-feedback

// Create FeedbackEvent node
CREATE CONSTRAINT feedback_event_id_unique IF NOT EXISTS
FOR (f:FeedbackEvent) REQUIRE f.event_id IS UNIQUE;

CREATE INDEX feedback_event_pattern_id_idx IF NOT EXISTS
FOR (f:FeedbackEvent) ON (f.pattern_id);

CREATE INDEX feedback_event_timestamp_idx IF NOT EXISTS
FOR (f:FeedbackEvent) ON (f.timestamp);

// Create ConceptDriftAlert node
CREATE CONSTRAINT drift_alert_id_unique IF NOT EXISTS
FOR (c:ConceptDriftAlert) REQUIRE c.alert_id IS UNIQUE;

// Create PatternVersion node
CREATE CONSTRAINT pattern_version_id_unique IF NOT EXISTS
FOR (pv:PatternVersion) REQUIRE pv.version_id IS UNIQUE;

// Create ABExperiment node
CREATE CONSTRAINT ab_experiment_id_unique IF NOT EXISTS
FOR (e:ABExperiment) REQUIRE e.experiment_id IS UNIQUE;

// Create relationships
// (:Pattern)-[:HAS_FEEDBACK]->(:FeedbackEvent)
// (:Pattern)-[:HAS_DRIFT_ALERT]->(:ConceptDriftAlert)
// (:Pattern)-[:HAS_VERSION]->(:PatternVersion)
// (:PatternVersion)-[:PART_OF_EXPERIMENT]->(:ABExperiment)
// (:PatternVersion)-[:SUPERSEDES]->(:PatternVersion)

// Update schema version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "2.2.0",
    sv.migrated_at = datetime(),
    sv.migration_name = "add_optimization_loop",
    sv.description = "Added FeedbackEvent, DriftAlert, PatternVersion, ABExperiment for Phase 3.3";
```

---

## Migration Workflow

### 1. Pre-Migration Checklist

```bash
# Check current schema version
python scripts/check_schema_version.py
# Expected: Current version, migration history

# Backup database
neo4j-admin database dump neo4j --to-path=/backups/neo4j_pre_migration.dump

# Verify backup
ls -lh /backups/neo4j_pre_migration.dump
```

### 2. Running Migrations

```python
# migration_runner.py
import neo4j
import sys
from pathlib import Path

MIGRATIONS = {
    "1.0.0": None,  # Base
    "1.1.0": "migrations/v1.1.0_add_danger_scores.cypher",
    "1.2.0": "migrations/v1.2.0_add_fsm_classification.cypher",
    "1.3.0": "migrations/v1.3.0_add_guard_decisions.cypher",
    "2.0.0": "migrations/v2.0.0_add_pattern_extraction.cypher",
    "2.1.0": "migrations/v2.1.0_add_pattern_ranking.cypher",
    "2.2.0": "migrations/v2.2.0_add_optimization_loop.cypher",
}

def get_current_version(driver) -> str:
    with driver.session() as session:
        result = session.run("""
            MATCH (sv:SchemaVersion {singleton: true})
            RETURN sv.version as version
        """)
        record = result.single()
        return record["version"] if record else "1.0.0"

def run_migration(driver, version: str, script_path: str):
    print(f"Running migration {version}...")

    with open(script_path) as f:
        cypher = f.read()

    with driver.session() as session:
        # Run in transaction
        session.run(cypher)

    print(f"✅ Migration {version} complete")

def migrate(target_version: str = None):
    driver = neo4j.GraphDatabase.driver("bolt://localhost:7687")

    current = get_current_version(driver)
    print(f"Current schema version: {current}")

    # Find migrations to run
    versions = sorted(MIGRATIONS.keys())
    current_idx = versions.index(current)
    target_idx = versions.index(target_version) if target_version else len(versions) - 1

    for version in versions[current_idx + 1:target_idx + 1]:
        script_path = MIGRATIONS[version]
        if script_path:
            run_migration(driver, version, script_path)

    driver.close()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(target)
```

### 3. Verification

```cypher
// After migration, verify
MATCH (sv:SchemaVersion {singleton: true})
RETURN sv.version as current_version,
       sv.migrated_at as migrated_at,
       sv.migration_name as last_migration;

// Verify new schema elements exist
CALL db.schema.nodeTypeProperties() YIELD nodeType, propertyName
WHERE nodeType IN ["Pattern", "RankScore", "FeedbackEvent"]
RETURN nodeType, collect(propertyName) as properties
ORDER BY nodeType;
```

---

## Backward Compatibility Strategy

### Adding Properties (Safe)

```cypher
// Always use MERGE with default values
MATCH (s:Step)
WHERE s.new_property IS NULL
SET s.new_property = $default_value;
```

### Adding Node Types (Safe)

New node types don't affect existing queries.

### Removing Properties (Breaking)

```cypher
// Don't remove - deprecate instead
MATCH (s:Step)
SET s.old_property_deprecated = true
REMOVE s.old_property;  // Only after 2+ versions
```

### Relationship Changes (Careful)

```cypher
// If changing relationship type, create both during transition
MATCH (a:Pattern)-[old:OLD_REL]->(b:Trace)
CREATE (a)-[:NEW_REL {properties: old.properties}]->(b)
// Keep OLD_REL until all code updated
```

---

## Rollback Procedures

### Emergency Rollback

```bash
# Stop application
sudo systemctl stop grimoire

# Restore from backup
neo4j-admin database load neo4j --from-path=/backups/neo4j_pre_migration.dump

# Verify
python scripts/check_schema_version.py
```

### Graceful Rollback (Data Preserved)

```cypher
// Run rollback script (provided with each migration)
// Example: v1.1.0_rollback.cypher

// Move data to backup properties instead of deleting
MATCH (s:Step)
WHERE s.danger_ambiguity IS NOT NULL
SET s._backup_danger_ambiguity = s.danger_ambiguity
REMOVE s.danger_ambiguity,
       s.danger_adversarial,
       s.danger_irreversibility,
       s.danger_institutional;

// Restore version
MERGE (sv:SchemaVersion {singleton: true})
SET sv.version = "1.0.0",
    sv.rollback_at = datetime(),
    sv.rollback_reason = "Performance regression in danger queries";
```

---

## Environment-Specific Migrations

### Development

```bash
# Auto-migrate on startup
export NEO4J_AUTO_MIGRATE=true
export NEO4J_TARGET_VERSION=latest
```

### Staging

```bash
# Manual migration with verification
python scripts/migrate.py --target 2.1.0 --verify
```

### Production

```bash
# Blue-green deployment
# 1. Migrate standby database
# 2. Verify
# 3. Switch traffic
# 4. Monitor
python scripts/migrate.py --target 2.1.0 --backup --verify --dry-run
```

---

## Monitoring

```cypher
// Monitor migration health
MATCH (mh:MigrationHistory)
RETURN mh.version,
       mh.applied_at,
       mh.duration_ms,
       mh.nodes_created,
       mh.relationships_created
ORDER BY mh.applied_at DESC
LIMIT 10;

// Check for schema inconsistencies
MATCH (s:Step)
WHERE s.danger_ambiguity IS NOT NULL 
  AND (s.danger_adversarial IS NULL OR s.danger_irreversibility IS NULL)
RETURN count(s) as incomplete_danger_scores;
```

---

## Appendix: Full Schema Versions

| Version | Features | Node Types | Relationship Types |
|---------|----------|------------|-------------------|
| 1.0.0 | Phase 1 (001) | Trace, Step, Edge, SourceRef | CONTAINS, NEXT, REVISES, ... |
| 1.1.0 | + Phase 2.1 (002) | + DangerScore (properties) | (none new) |
| 1.2.0 | + Phase 2.2 (003) | + FSMClassification (properties) | (none new) |
| 1.3.0 | + Phase 2.3 (004) | + GuardDecision | BLOCKED_BY_GUARD |
| 2.0.0 | + Phase 3.1 (005) | + Pattern, PatternStep, CostProfile | HAS_STEP, HAS_COST_PROFILE, MATCHES_TRACE |
| 2.1.0 | + Phase 3.2 (006) | + RankScore | HAS_RANKING |
| 2.2.0 | + Phase 3.3 (008) | + FeedbackEvent, DriftAlert, PatternVersion, ABExperiment | HAS_FEEDBACK, HAS_DRIFT_ALERT, HAS_VERSION, SUPERSEDES, PART_OF_EXPERIMENT |

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | AI Assistant | Initial migration guide |
