"""HuggingFace dataset loader for OpenThoughts datasets.

Supports both 114K and 1.2M variants with streaming and batch configuration.
"""

from typing import Any, Optional
from datasets import load_dataset, Dataset


class HFDatasetConfig:
    """Configuration for HuggingFace dataset loading."""
    
    def __init__(
        self,
        dataset_id: str = "open-thoughts/OpenThoughts-114k",
        split: str = "train",
        streaming: bool = False,
        limit: Optional[int] = None,
    ):
        """Initialize config.
        
        Args:
            dataset_id: HuggingFace dataset identifier
            split: Dataset split to load (default: "train")
            streaming: Use streaming mode for large datasets (True for 1.2M)
            limit: Maximum records to load (None = all)
        """
        self.dataset_id = dataset_id
        self.split = split
        self.streaming = streaming
        self.limit = limit


class HFDatasetLoader:
    """Loader for HuggingFace reasoning datasets."""
    
    def __init__(self, config: Optional[HFDatasetConfig] = None):
        self.config = config or HFDatasetConfig()
        self._dataset: Optional[Dataset] = None
    
    def load(self) -> Dataset:
        """Load dataset from HuggingFace.
        
        Returns:
            Dataset object
        """
        if self._dataset is None:
            print(
                f"Loading dataset: {self.config.dataset_id} "
                f"(split={self.config.split}, streaming={self.config.streaming})"
            )
            self._dataset = load_dataset(
                self.config.dataset_id,
                split=self.config.split,
                streaming=self.config.streaming,
            )
            
            if self.config.limit:
                self._dataset = self._dataset.select(range(self.config.limit))
        
        return self._dataset
    
    def get_records(self) -> list[dict[str, Any]]:
        """Get all records as list.
        
        Useful for batch processing in memory for small datasets.
        """
        dataset = self.load()
        return list(dataset)
