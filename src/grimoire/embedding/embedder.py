"""Text embedder with version binding and staleness tracking."""

import logging
from typing import Dict, Any, Optional
from grimoire.embedding.model_loader import EmbeddingModelLoader

logger = logging.getLogger(__name__)


class TextEmbedder:
    """Generate embeddings with version binding."""
    
    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedder.
        
        Args:
            model_id: Embedding model ID
        """
        self.loader = EmbeddingModelLoader(model_id)
        self.model, self.embedding_dim = self.loader.load()
    
    def embed_step_text(
        self,
        text: str,
        text_version: int = 1,
    ) -> tuple[list[float], Dict[str, Any]]:
        """Embed step text with version binding.
        
        Args:
            text: Step text to embed
            text_version: Version of this text
            
        Returns:
            Tuple of (embedding vector, metadata dict)
        """
        import hashlib
        
        # Generate embedding
        embeddings = self.loader.embed([text])
        embedding = embeddings[0]
        
        # Calculate content hash
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Metadata with version binding
        metadata = {
            "embedding_dim": self.embedding_dim,
            "text_version": text_version,
            "content_hash": content_hash,
            "embedding_stale": False,
        }
        
        return embedding, metadata
    
    def mark_stale(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Mark embedding as stale if text version changed.
        
        Args:
            metadata: Current metadata
            
        Returns:
            Updated metadata
        """
        metadata["embedding_stale"] = True
        return metadata
