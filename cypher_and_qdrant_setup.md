# qdrant_setup.py
# Minimal Qdrant client setup: create 3 collections + payload indexes.
#
# pip install qdrant-client
#
# Notes:
# - Choose your embedding dim & distance.
# - For speed, prefer COSINE for most text embeddings.
# - Payload indexes enable server-side filtering and faster query performance.

from __future__ import annotations

from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    OptimizersConfigDiff,
    HnswConfigDiff,
)


def ensure_collections(
    client: QdrantClient,
    dim: int,
    distance: Distance = Distance.COSINE,
    steps_collection: str = "steps",
    windows_collection: str = "step_windows",
    patterns_collection: str = "patterns",
) -> None:
    # A couple of sane defaults; tune later.
    hnsw = HnswConfigDiff(m=16, ef_construct=200)
    optim = OptimizersConfigDiff(default_segment_number=2)

    def create_if_missing(name: str) -> None:
        existing = {c.name for c in client.get_collections().collections}
        if name in existing:
            return
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=distance),
            hnsw_config=hnsw,
            optimizers_config=optim,
        )

    create_if_missing(steps_collection)
    create_if_missing(windows_collection)
    create_if_missing(patterns_collection)

    # ---------------------------
    # Payload indexes (Steps)
    # ---------------------------
    # Keyword fields
    for key in ["step_id", "trace_id", "actor", "role", "fsm_id", "fsm_state", "domain", "tool", "license", "sensitivity"]:
        client.create_payload_index(
            collection_name=steps_collection,
            field_name=key,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # Integer fields
    for key in ["index"]:
        client.create_payload_index(
            collection_name=steps_collection,
            field_name=key,
            field_schema=PayloadSchemaType.INTEGER,
        )

    # Bool fields
    for key in ["has_tool_call"]:
        client.create_payload_index(
            collection_name=steps_collection,
            field_name=key,
            field_schema=PayloadSchemaType.BOOL,
        )

    # Float fields (danger)
    for key in ["danger_ambiguity", "danger_adversarial", "danger_irreversibility", "danger_institutional"]:
        client.create_payload_index(
            collection_name=steps_collection,
            field_name=key,
            field_schema=PayloadSchemaType.FLOAT,
        )

    # "tags" as keyword array; Qdrant indexes array fields with KEYWORD schema.
    client.create_payload_index(
        collection_name=steps_collection,
        field_name="tags",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # Optional: source fields (arrays)
    for key in ["source_type", "source_id"]:
        client.create_payload_index(
            collection_name=steps_collection,
            field_name=key,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # ---------------------------
    # Payload indexes (Windows)
    # ---------------------------
    for key in ["window_id", "trace_id", "fsm_id", "fsm_state", "domain", "license", "sensitivity"]:
        client.create_payload_index(
            collection_name=windows_collection,
            field_name=key,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    for key in ["start_index", "k"]:
        client.create_payload_index(
            collection_name=windows_collection,
            field_name=key,
            field_schema=PayloadSchemaType.INTEGER,
        )

    client.create_payload_index(
        collection_name=windows_collection,
        field_name="has_tool_call",
        field_schema=PayloadSchemaType.BOOL,
    )

    for key in ["danger_ambiguity", "danger_adversarial", "danger_irreversibility", "danger_institutional"]:
        client.create_payload_index(
            collection_name=windows_collection,
            field_name=key,
            field_schema=PayloadSchemaType.FLOAT,
        )

    client.create_payload_index(
        collection_name=windows_collection,
        field_name="tags",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # step_ids is an array of ids; KEYWORD index makes filtering possible (e.g., contains)
    client.create_payload_index(
        collection_name=windows_collection,
        field_name="step_ids",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # ---------------------------
    # Payload indexes (Patterns)
    # ---------------------------
    for key in ["pattern_id", "type", "name", "fsm_id", "miner_version", "schema_version"]:
        client.create_payload_index(
            collection_name=patterns_collection,
            field_name=key,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # arrays
    for key in ["allowed_states", "domains", "required_tags", "forbidden_tags"]:
        client.create_payload_index(
            collection_name=patterns_collection,
            field_name=key,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # quality fields
    client.create_payload_index(
        collection_name=patterns_collection,
        field_name="quality_support",
        field_schema=PayloadSchemaType.INTEGER,
    )
    client.create_payload_index(
        collection_name=patterns_collection,
        field_name="quality_success_proxy",
        field_schema=PayloadSchemaType.FLOAT,
    )

    # danger constraints on patterns (optional but useful)
    for key in [
        "min_danger_ambiguity", "min_danger_adversarial", "min_danger_irreversibility", "min_danger_institutional",
        "max_danger_ambiguity", "max_danger_adversarial", "max_danger_irreversibility", "max_danger_institutional",
    ]:
        client.create_payload_index(
            collection_name=patterns_collection,
            field_name=key,
            field_schema=PayloadSchemaType.FLOAT,
        )


if __name__ == "__main__":
    # Local Qdrant
    client = QdrantClient(url="http://localhost:6333")

    # Set this to your embedding model dimension
    EMBED_DIM = 3072  # example; change to your model

    ensure_collections(client, dim=EMBED_DIM)
    print("Qdrant collections + payload indexes ensured.")
