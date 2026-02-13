"""Schema validation for ingested data.

Validates Trace, Step, and Edge objects against Pydantic schema.
"""

from typing import Any, Dict, Optional
from pydantic import ValidationError
from grimoire.core.schema.models import Trace, Step, Edge


class SchemaValidator:
    """Validates canonical schema objects."""
    
    @staticmethod
    def validate_trace(data: Dict[str, Any]) -> tuple[Optional[Trace], Optional[str]]:
        """Validate and parse Trace data.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            Tuple of (Trace object or None, error message or None)
        """
        try:
            trace = Trace(**data)
            return trace, None
        except ValidationError as e:
            return None, str(e)
    
    @staticmethod
    def validate_step(data: Dict[str, Any]) -> tuple[Optional[Step], Optional[str]]:
        """Validate and parse Step data.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            Tuple of (Step object or None, error message or None)
        """
        try:
            step = Step(**data)
            return step, None
        except ValidationError as e:
            return None, str(e)
    
    @staticmethod
    def validate_edge(data: Dict[str, Any]) -> tuple[Optional[Edge], Optional[str]]:
        """Validate and parse Edge data.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            Tuple of (Edge object or None, error message or None)
        """
        try:
            edge = Edge(**data)
            return edge, None
        except ValidationError as e:
            return None, str(e)
