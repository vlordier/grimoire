"""Embedding model loader with configurable model support.

Supports local models (all-MiniLM-L6-v2) and remote APIs (OpenAI, etc.).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingModelLoader:
    """Load and manage embedding models."""
    
    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize model loader.
        
        Args:
            model_id: HuggingFace model ID or OpenAI model name
        """
        self.model_id = model_id
        self.model = None
        self.dimensions = None
    
    def load(self) -> tuple[any, int]:
        """Load embedding model.
        
        Returns:
            Tuple of (model, embedding_dimensions)
        """
        if self.model is not None:
            return self.model, self.dimensions
        
        logger.info(f"Loading embedding model: {self.model_id}")
        
        # Local model via sentence-transformers
        if "all-MiniLM-L6-v2" in self.model_id:
            try:
                from sentence_transformers import SentenceTransformer
                
                self.model = SentenceTransformer(self.model_id)
                self.dimensions = 384
                logger.info(f"Loaded {self.model_id} (dim={self.dimensions})")
                return self.model, self.dimensions
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        
        # For other models, would add support for:
        # - Other sentence-transformers models
        # - OpenAI API
        # - Other remote APIs
        
        raise ValueError(f"Unsupported embedding model: {self.model_id}")
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        model, _ = self.load()
        
        # Sentence-transformers interface
        if hasattr(model, 'encode'):
            embeddings = model.encode(texts, convert_to_numpy=False)
            return [e.tolist() if hasattr(e, 'tolist') else e for e in embeddings]
        
        raise RuntimeError(f"Model {self.model_id} does not support encode()")
