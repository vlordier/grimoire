#!/usr/bin/env python3
"""
Phase 1 Pydantic v2 validation script.
Verifies all enums, constraints, and field validators work correctly.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime

# Test canonical enums
class DomainTag(str, Enum):
    GENERAL = "general"
    SOFTWARE = "software"
    ML = "ml"
    DATA = "data"
    SECURITY = "security"
    PRODUCT = "product"
    LEGAL = "legal"
    HEALTH = "health"
    FINANCE = "finance"

class StepRole(str, Enum):
    GOAL = "goal"
    QUESTION = "question"
    PLAN = "plan"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    CRITIQUE = "critique"
    REVISION = "revision"
    DECISION = "decision"
    VERIFICATION = "verification"
    SUMMARY = "summary"
    OTHER = "other"

class EdgeType(str, Enum):
    NEXT = "next"
    SUPPORTS = "supports"
    REFUTES = "refutes"

# Test ID pattern validation
class TestIDModel(BaseModel):
    trace_id: str = Field(pattern="^[a-zA-Z0-9]{12}-[a-zA-Z0-9]{8}$")
    step_id: str = Field(pattern="^[a-zA-Z0-9]{26}$")  # ULID
    content_hash: str = Field(pattern="^[a-f0-9]{64}$")  # SHA256
    
    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, v):
        if len(v) != 21:  # 12 + "-" + 8
            raise ValueError(f"trace_id must be 21 chars, got {len(v)}")
        return v

# Test list constraints (Pydantic v2 syntax)
class TestListModel(BaseModel):
    vector: List[float] = Field(min_length=384, max_length=384)
    supports: List[str] = Field(default_factory=list)

# Test danger score constraints
class TestDangerModel(BaseModel):
    danger_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0)
    danger_adversarial: float = Field(default=0.0, ge=0.0, le=1.0)

# Test record_id validator
from typing import Literal

class TestRecordID(BaseModel):
    record_id: Optional[str] = Field(default=None)
    
    @field_validator("record_id")
    @classmethod
    def record_id_format(cls, v):
        if v is not None:
            if len(v) > 300:
                raise ValueError(f"record_id must be ≤ 300 chars; got {len(v)}")
            if not all(c.isalnum() or c == '_' for c in v):
                raise ValueError(f"record_id must be alphanumeric + underscore only")
        return v

# Run tests
print("=" * 60)
print("PHASE 1 PYDANTIC V2 VALIDATION")
print("=" * 60)

try:
    # Test 1: Enums
    print("\n[1/5] Testing canonical enums...")
    assert len(DomainTag) == 9, "DomainTag should have 9 values"
    assert len(StepRole) == 12, "StepRole should have 12 values"
    assert len(EdgeType) == 3, "EdgeType sample has 3 values"
    print("  ✅ All enums have correct values")
    
    # Test 2: ID patterns
    print("\n[2/5] Testing ID pattern validation...")
    model_id = TestIDModel(
        trace_id="abcdef123456-abcd1234",
        step_id="01ARZ3NDEKTSV4RRFFQ69G5FA",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert model_id.trace_id == "abcdef123456-abcd1234"
    print("  ✅ ID patterns validated correctly")
    
    # Test 3: List constraints (min_length, max_length)
    print("\n[3/5] Testing Pydantic v2 list constraints (min_length/max_length)...")
    list_model = TestListModel(vector=[0.1] * 384)
    assert len(list_model.vector) == 384
    try:
        TestListModel(vector=[0.1] * 383)  # Should fail
        print("  ❌ Should have rejected vector with < 384 dims")
        exit(1)
    except ValueError:
        print("  ✅ List constraints work correctly (rejected 383-dim vector)")
    
    # Test 4: Danger score constraints
    print("\n[4/5] Testing danger score constraints (0.0 ≤ x ≤ 1.0)...")
    danger_model = TestDangerModel(
        danger_ambiguity=0.5,
        danger_adversarial=0.75
    )
    assert danger_model.danger_ambiguity == 0.5
    try:
        TestDangerModel(danger_ambiguity=1.5)  # Should fail
        print("  ❌ Should have rejected danger_ambiguity > 1.0")
        exit(1)
    except ValueError:
        print("  ✅ Danger constraints work correctly")
    
    # Test 5: record_id validator
    print("\n[5/5] Testing record_id validator...")
    record_model = TestRecordID(record_id="trace_12345_v2")
    assert record_model.record_id == "trace_12345_v2"
    try:
        TestRecordID(record_id="invalid@record")  # Should fail
        print("  ❌ Should have rejected record_id with '@'")
        exit(1)
    except ValueError:
        print("  ✅ record_id validator works correctly")
    
    print("\n" + "=" * 60)
    print("✅ ALL PHASE 1 PYDANTIC V2 VALIDATIONS PASSED")
    print("=" * 60)
    print("\nPhase 1 is ready for implementation!")
    
except Exception as e:
    print(f"\n❌ VALIDATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
