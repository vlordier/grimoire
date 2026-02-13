"""Qdrant vector storage for embeddings.

Implements Constitution Principle VII (Dual-Store Architecture):
- Stores step embeddings in Qdrant with version binding
- Maintains filterable payloads (domain, FSM, danger signals)
- Supports semantic search and filtered queries
- Creates collections on first run

References:
- Plan: specs/001-canonical-schema-implementation/plan.md
- Contract: specs/001-canonical-schema-implementation/contracts/retrieval-api.md
"""

import logging
from typing import Dict, List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    HnswConfigDiff,
)

logger = logging.getLogger(__name__)


class QdrantStorageException(Exception):
    """Base exception for Qdrant storage errors."""
    pass


class QdrantStorage:
    """Qdrant vector storage for embeddings.
    
    Manages step embeddings with version binding and filterable metadata.
    """
    
    def __init__(self, url: str, embedding_dim: int = 384):
        """Initialize Qdrant storage.
        
        Args:
            url: Qdrant server URL (e.g., "http://localhost:6333")
            embedding_dim: Embedding dimensionality (default: 384 for all-MiniLM-L6-v2)
            
        Raises:
            QdrantStorageException: If connection fails
        """
        try:
            self.client = QdrantClient(url=url)
            self.embedding_dim = embedding_dim
            self.client.get_collections()  # Verify connection
            logger.info(f"Connected to Qdrant at {url}")
        except Exception as e:
            raise QdrantStorageException(f"Failed to connect to Qdrant: {e}")
    
    def create_collections(self):
        """Create required collections on first run.
        
        Creates:
        - steps: Step embeddings with metadata
        - step_windows: Window embeddings for context
        """
        try:
            # Create steps collection
            self.client.recreate_collection(
                collection_name="steps",
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
            )
            logger.info("Created 'steps' collection")
            
            # Create step_windows collection
            self.client.recreate_collection(
                collection_name="step_windows",
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
            )
            logger.info("Created 'step_windows' collection")
            
        except Exception as e:
            logger.warning(f"Collection creation issue: {e}")
            # Collections might already exist, which is fine
    
    def insert_step_embedding(
        self,
        step_id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> bool:
        """Insert a step embedding with payload.
        
        Args:
            step_id: Step ID (becomes point_id)
            embedding: Vector embedding (list of floats)
            payload: Metadata (trace_id, domain, role, danger_*, etc.)
            
        Returns:
            True if successful
        """
        try:
            # Convert step_id to integer hash for point_id
            point_id = hash(step_id) & 0x7FFFFFFF  # Keep positive
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            
            self.client.upsert(
                collection_name="steps",
                points=[point],
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert embedding for {step_id}: {e}")
            raise QdrantStorageException(f"Embedding insertion failed: {e}")
    
    def batch_insert_embeddings(
        self,
        embeddings: List[tuple[str, List[float], Dict[str, Any]]],
    ) -> int:
        """Insert multiple embeddings (step_id, vector, payload).
        
        Args:
            embeddings: List of (step_id, vector, payload) tuples
            
        Returns:
            Number of embeddings successfully inserted
        """
        points = []
        for step_id, vector, payload in embeddings:
            point_id = hash(step_id) & 0x7FFFFFFF
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        
        try:
            self.client.upsert(
                collection_name="steps",
                points=points,
            )
            logger.info(f"Inserted {len(points)} embeddings")
            return len(points)
        except Exception as e:
            logger.error(f"Batch embedding insertion failed: {e}")
            raise QdrantStorageException(f"Batch insertion failed: {e}")
    
    def search_similar_steps(
        self,
        query_embedding: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for similar steps.
        
        Args:
            query_embedding: Query vector
            limit: Max results to return
            
        Returns:
            List of search results with scores and payloads
        """
        try:
            results = self.client.search(
                collection_name="steps",
                query_vector=query_embedding,
                limit=limit,
            )
            
            return [
                {
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise QdrantStorageException(f"Search failed: {e}")
    
    def search_with_filter(
        self,
        query_embedding: List[float],
        filter_dict: Dict[str, Any],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search with metadata filters.
        
        Args:
            query_embedding: Query vector
            filter_dict: Qdrant filter (e.g., {"domain": "software"})
            limit: Max results
            
        Returns:
            Filtered search results
        """
        try:
            # Simple filtering: search all and filter in Python
            # For production, use Qdrant's filter syntax
            results = self.search_similar_steps(query_embedding, limit=limit * 2)
            
            # Filter payloads
            filtered = []
            for r in results:
                if all(r["payload"].get(k) == v for k, v in filter_dict.items()):
                    filtered.append(r)
                    if len(filtered) >= limit:
                        break
            
            return filtered
            
        except Exception as e:
            logger.error(f"Filtered search failed: {e}")
            raise QdrantStorageException(f"Filtered search failed: {e}")
