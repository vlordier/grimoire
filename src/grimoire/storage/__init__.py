"""Package initialization for storage module."""

from grimoire.storage.neo4j import Neo4jStorage, Neo4jStorageException

__all__ = ["Neo4jStorage", "Neo4jStorageException"]
