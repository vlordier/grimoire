"""Neo4j graph storage for canonical schema.

Implements Constitution Principle VII (Dual-Store Architecture):
- Stores Trace, Step, Edge nodes and relationships
- Maintains referential integrity via ULID keys
- Supports batch insertions with transaction control
- Provides graph queries for traversal and filtering

References:
- Plan: specs/001-canonical-schema-implementation/plan.md
- Contract: specs/001-canonical-schema-implementation/contracts/storage-api.md
- Constitution Principle VII: Dual-Store Architecture
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from neo4j import Driver, Session, Transaction, exceptions
from neo4j import GraphDatabase

from grimoire.core.schema.models import (
    Trace,
    Step,
    Edge,
    EdgeType,
)


logger = logging.getLogger(__name__)


class Neo4jStorageException(Exception):
    """Base exception for Neo4j storage errors."""
    pass


class Neo4jStorage:
    """Neo4j graph storage for canonical schema entities.
    
    Manages Trace, Step, and Edge persistence with transaction support
    and referential integrity constraints per Constitution Principle VI.
    """
    
    def __init__(
        self,
        uri: str,
        auth: tuple = None,
        database: str = "neo4j",
    ):
        """Initialize Neo4j storage.
        
        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            auth: Tuple of (username, password)
            database: Database name to use
            
        Raises:
            Neo4jStorageException: If connection fails
        """
        try:
            self.driver: Driver = GraphDatabase.driver(uri, auth=auth)
            self.database = database
            self._verify_connection()
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            raise Neo4jStorageException(f"Failed to connect to Neo4j: {e}")
    
    def _verify_connection(self):
        """Verify Neo4j connection is active."""
        try:
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
        except Exception as e:
            raise Neo4jStorageException(f"Connection verification failed: {e}")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_indexes(self):
        """Create required indexes for performance.
        
        Per plan: Index on (domain), (fsm_id, fsm_state), (role)
        """
        with self.driver.session(database=self.database) as session:
            # Trace indexes
            session.run("CREATE INDEX idx_trace_domain IF NOT EXISTS FOR (t:Trace) ON (t.domain)")
            session.run("CREATE INDEX idx_trace_id IF NOT EXISTS FOR (t:Trace) ON (t.trace_id)")
            
            # Step indexes
            session.run("CREATE INDEX idx_step_id IF NOT EXISTS FOR (s:Step) ON (s.step_id)")
            session.run("CREATE INDEX idx_step_trace_id IF NOT EXISTS FOR (s:Step) ON (s.trace_id)")
            session.run("CREATE INDEX idx_step_fsm IF NOT EXISTS FOR (s:Step) ON (s.fsm_id, s.fsm_state)")
            session.run("CREATE INDEX idx_step_role IF NOT EXISTS FOR (s:Step) ON (s.role)")
            
            logger.info("Created Neo4j indexes")
    
    def create_constraints(self):
        """Create uniqueness constraints.
        
        Per plan: UNIQUE (trace_id), UNIQUE (step_id)
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (t:Trace) REQUIRE t.trace_id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (s:Step) REQUIRE s.step_id IS UNIQUE"
            )
            logger.info("Created Neo4j constraints")
    
    def insert_trace(self, trace: Trace, session: Optional[Session] = None) -> bool:
        """Insert a Trace node into Neo4j.
        
        Args:
            trace: Trace object to persist
            session: Optional existing session (for batch operations)
            
        Returns:
            True if successful
            
        Raises:
            Neo4jStorageException: If insertion fails
        """
        try:
            def _insert(tx: Transaction):
                # Flatten provenance for storage
                query = """
                CREATE (t:Trace {
                    trace_id: $trace_id,
                    title: $title,
                    domain: $domain,
                    problem: $problem,
                    tags: $tags,
                    status: $status,
                    trace_version: $trace_version,
                    n_steps: $n_steps,
                    is_duplicate: $is_duplicate,
                    duplicate_of: $duplicate_of,
                    created_at: datetime($created_at),
                    updated_at: datetime($updated_at),
                    provenance_sources: $provenance_sources,
                    provenance_license: $provenance_license,
                    provenance_sensitivity: $provenance_sensitivity,
                    provenance_ingested_at: datetime($provenance_ingested_at),
                    provenance_pipeline_version: $provenance_pipeline_version,
                    provenance_schema_version: $provenance_schema_version
                })
                RETURN t.trace_id as trace_id
                """
                
                params = {
                    "trace_id": trace.trace_id,
                    "title": trace.title,
                    "domain": trace.domain.value,
                    "problem": trace.problem,
                    "tags": trace.tags,
                    "status": trace.status,
                    "trace_version": trace.trace_version,
                    "n_steps": trace.n_steps,
                    "is_duplicate": trace.is_duplicate,
                    "duplicate_of": trace.duplicate_of,
                    "created_at": trace.created_at.isoformat(),
                    "updated_at": trace.updated_at.isoformat(),
                    "provenance_sources": [s.dict() for s in trace.provenance_sources],
                    "provenance_license": trace.provenance_license.value,
                    "provenance_sensitivity": trace.provenance_sensitivity.value,
                    "provenance_ingested_at": trace.provenance_ingested_at.isoformat(),
                    "provenance_pipeline_version": trace.provenance_pipeline_version,
                    "provenance_schema_version": trace.provenance_schema_version,
                }
                
                result = tx.run(query, params)
                return result.single()
            
            if session:
                _insert(session)
            else:
                with self.driver.session(database=self.database) as s:
                    s.write_transaction(_insert)
            
            return True
            
        except exceptions.ConstraintError as e:
            logger.error(f"Constraint violation for trace {trace.trace_id}: {e}")
            raise Neo4jStorageException(f"Duplicate trace_id: {trace.trace_id}")
        except Exception as e:
            logger.error(f"Failed to insert trace {trace.trace_id}: {e}")
            raise Neo4jStorageException(f"Trace insertion failed: {e}")
    
    def insert_step(self, step: Step, session: Optional[Session] = None) -> bool:
        """Insert a Step node and HAS_STEP relationship.
        
        Args:
            step: Step object to persist
            session: Optional existing session
            
        Returns:
            True if successful
            
        Raises:
            Neo4jStorageException: If insertion fails
        """
        try:
            def _insert(tx: Transaction):
                # Create Step node and link to Trace
                query = """
                MATCH (t:Trace {trace_id: $trace_id})
                CREATE (s:Step {
                    step_id: $step_id,
                    trace_id: $trace_id,
                    index: $index,
                    actor: $actor,
                    role: $role,
                    fsm_id: $fsm_id,
                    fsm_state: $fsm_state,
                    created_at: datetime($created_at)
                })
                CREATE (t)-[:HAS_STEP]->(s)
                RETURN s.step_id as step_id
                """
                
                params = {
                    "step_id": step.step_id,
                    "trace_id": step.trace_id,
                    "index": step.index,
                    "actor": step.actor,
                    "role": step.role.value,
                    "fsm_id": step.fsm_id,
                    "fsm_state": step.fsm_state.value if step.fsm_state else None,
                    "created_at": step.created_at.isoformat(),
                }
                
                result = tx.run(query, params)
                return result.single()
            
            if session:
                _insert(session)
            else:
                with self.driver.session(database=self.database) as s:
                    s.write_transaction(_insert)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert step {step.step_id}: {e}")
            raise Neo4jStorageException(f"Step insertion failed: {e}")
    
    def insert_edge(self, edge: Edge, session: Optional[Session] = None) -> bool:
        """Insert an Edge relationship between nodes.
        
        Args:
            edge: Edge object to persist
            session: Optional existing session
            
        Returns:
            True if successful
        """
        try:
            def _insert(tx: Transaction):
                # Create edge between steps or other nodes
                rel_type = edge.edge_type.value  # e.g., "NEXT", "DEPENDS_ON"
                
                query = f"""
                MATCH (src {{step_id: $src_id}})
                MATCH (dst {{step_id: $dst_id}})
                CREATE (src)-[:{rel_type} {{weight: $weight}}]->(dst)
                RETURN src.step_id as src_id
                """
                
                params = {
                    "src_id": edge.src_id,
                    "dst_id": edge.dst_id,
                    "weight": edge.weight,
                }
                
                tx.run(query, params)
            
            if session:
                _insert(session)
            else:
                with self.driver.session(database=self.database) as s:
                    s.write_transaction(_insert)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert edge {edge.edge_id}: {e}")
            raise Neo4jStorageException(f"Edge insertion failed: {e}")
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a Trace by ID.
        
        Args:
            trace_id: The trace_id to retrieve
            
        Returns:
            Dict representation of Trace or None if not found
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (t:Trace {trace_id: $trace_id}) RETURN t",
                trace_id=trace_id,
            )
            record = result.single()
            if record:
                return dict(record["t"])
            return None
    
    def get_trace_steps(self, trace_id: str) -> List[Dict[str, Any]]:
        """Retrieve all Steps for a Trace in index order.
        
        Args:
            trace_id: The trace_id to retrieve steps for
            
        Returns:
            List of Step dicts ordered by index
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (t:Trace {trace_id: $trace_id})-[:HAS_STEP]->(s:Step)
                RETURN s ORDER BY s.index ASC
                """,
                trace_id=trace_id,
            )
            return [dict(record["s"]) for record in result]
    
    def batch_insert_traces(self, traces: List[Trace]) -> int:
        """Insert multiple Traces transactionally.
        
        Args:
            traces: List of Trace objects
            
        Returns:
            Number of traces successfully inserted
            
        Raises:
            Neo4jStorageException: If batch fails (rollback occurs)
        """
        inserted = 0
        try:
            with self.driver.session(database=self.database) as session:
                with session.begin_transaction() as tx:
                    for trace in traces:
                        try:
                            self.insert_trace(trace, session=tx)
                            inserted += 1
                        except Exception as e:
                            logger.warning(f"Skipping trace {trace.trace_id}: {e}")
                            # Continue with next trace in batch
            
            logger.info(f"Inserted {inserted}/{len(traces)} traces")
            return inserted
            
        except Exception as e:
            logger.error(f"Batch insert transaction failed: {e}")
            raise Neo4jStorageException(f"Batch insertion failed: {e}") from e
