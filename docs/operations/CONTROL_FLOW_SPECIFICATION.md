# Control Flow Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: Pattern Detection & Extraction (Feature 005)  
**Status**: Specification

---

## Overview

This document clarifies control flow patterns (if/else, for loops, while loops) in the context of Grimoire's reasoning engine. It provides:

1. **Code implementations** for enforcing and executing control flow deterministically
2. **Prompts** for adapting control flow patterns to specific problems
3. **Patterns** for counting, percentage evaluation, and loop enforcement

---

## Quick Reference Table

| Part | Content | Key Classes |
|------|---------|-------------|
| **Part 1** | Core Primitives | `IfElseControlFlow`, `EnumeratedForLoop`, `WhileLoop` |
| **Part 2** | Deterministic Functions | `PercentageEvaluator`, `Counter`, `AdaptiveCounter` |
| **Part 3** | Prompt Templates | Branch, Loop, Percentage prompts |
| **Part 4** | Complete Examples | Pattern ranking, score optimization |
| **Part 5** | Composed Patterns | `SwitchMatch`, `TryCatchFinally`, `Pipeline` |
| **Part 6** | Pattern Detection | `ControlFlowDetector`, `LoopEnforcer` |
| **Part 7** | Testing | Property-based tests with Hypothesis |
| **Part 8** | Extensions | `ControlFlowBuilder` for custom patterns |

---

## Part 1: Core Control Flow Primitives

### 1.1 Branching (If/Else)

```python
# core/control_flow/branching.py
from typing import Callable, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass


class ConditionType(str, Enum):
    """Types of conditions for branching."""
    THRESHOLD = "threshold"           # Value comparison
    MEMBER_OF = "member_of"           # Set membership
    PATTERN_MATCH = "pattern_match"    # Regex/string match
    COMPOSITE = "composite"           # AND/OR/NOT combinations


@dataclass
class BranchCondition:
    """A condition that determines which branch to take."""
    condition_type: ConditionType
    expression: str                   # The condition expression
    evaluator: Optional[Callable] = None  # Function to evaluate
    
    def evaluate(self, context: dict) -> bool:
        """Evaluate the condition against context."""
        if self.evaluator:
            return self.evaluator(context)
        # Default: evaluate expression as Python code
        return eval(self.expression, {"context": context})


class Branch:
    """A branch in conditional logic."""
    name: str
    condition: Optional[BranchCondition] = None
    action: Callable[[dict], dict]
    
    def execute(self, context: dict) -> dict:
        """Execute the branch action."""
        return self.action(context)


class IfElseControlFlow:
    """
    Implements if/else control flow with deterministic evaluation.
    
    Usage:
        if_else = IfElseControlFlow()
        if_else.when(lambda c: c["score"] > 0.8, high_priority_action)
        if_else.when(lambda c: c["score"] > 0.5, medium_priority_action)
        if_else.otherwise(default_action)
        result = if_else.execute(context)
    """
    
    def __init__(self):
        self.branches: List[Branch] = []
        self.default_branch: Optional[Branch] = None
    
    def when(self, condition: Callable[[dict], bool], action: Callable[[dict], dict]) -> "IfElseControlFlow":
        """Add a condition → action branch."""
        branch = Branch(
            name=f"branch_{len(self.branches)}",
            condition=BranchCondition(
                condition_type=ConditionType.THRESHOLD,
                expression="",
                evaluator=condition
            ),
            action=action
        )
        self.branches.append(branch)
        return self
    
    def otherwise(self, action: Callable[[dict], dict]) -> "IfElseControlFlow":
        """Add the default branch (executed when no conditions match)."""
        self.default_branch = Branch(
            name="default",
            action=action
        )
        return self
    
    def execute(self, context: dict) -> dict:
        """Execute the first matching branch."""
        for branch in self.branches:
            if branch.condition and branch.condition.evaluator(context):
                return branch.action(context)
        
        if self.default_branch:
            return self.default_branch.action(context)
        
        return context  # Return unchanged if no branches


# Example: Pattern danger classification
def classify_pattern_danger(context: dict) -> dict:
    """Classify pattern based on danger score."""
    
    danger_score = context.get("danger_score", 0.0)
    
    if_else = IfElseControlFlow()
    
    # High danger: block execution
    if_else.when(
        lambda c: c.get("danger_score", 0) >= 0.8,
        lambda c: {**c, "action": "BLOCK", "reason": "Critical danger level"}
    )
    
    # Medium danger: require verification
    if_else.when(
        lambda c: 0.5 <= c.get("danger_score", 0) < 0.8,
        lambda c: {**c, "action": "VERIFY", "reason": "Medium danger - human review required"}
    )
    
    # Low danger: proceed with logging
    if_else.when(
        lambda c: 0.2 <= c.get("danger_score", 0) < 0.5,
        lambda c: {**c, "action": "PROCEED_LOG", "reason": "Low danger - proceed with logging"}
    )
    
    # Very low: auto-approve
    if_else.otherwise(
        lambda c: {**c, "action": "AUTO_APPROVE", "reason": "Minimal danger"}
    )
    
    return if_else.execute({"danger_score": danger_score})


# Usage
result = classify_pattern_danger({"danger_score": 0.75})
# Output: {"danger_score": 0.75, "action": "VERIFY", "reason": "Medium danger - human review required"}
```

---

### 1.2 For Loops (Fixed Iteration)

```python
# core/control_flow/iteration.py
from typing import Callable, List, Any, Optional, TypeVar, Generic
from dataclasses import dataclass
from pydantic import BaseModel, Field


T = TypeVar('T')
R = TypeVar('R')


class ForLoop(Generic[T, R]):
    """
    Implements for-loop iteration with deterministic execution.
    
    Usage:
        loop = ForLoop(items=candidates)
        results = loop.execute(
            transformer=lambda item: process(item),
            aggregator=lambda results: combine(results)
        )
    """
    
    def __init__(self, items: List[T]):
        self.items = items
        self.results: List[R] = []
        self.iteration_count: int = 0
        self.max_iterations: Optional[int] = None
    
    def with_limit(self, max_iterations: int) -> "ForLoop[T, R]":
        """Set maximum iterations (for safety)."""
        self.max_iterations = max_iterations
        return self
    
    def execute(
        self,
        transformer: Callable[[T, int], R],
        aggregator: Callable[[List[R]], Any] = None
    ) -> List[R] | Any:
        """
        Execute transformation on each item.
        
        Args:
            transformer: Function to apply to each item (item, index) -> result
            aggregator: Optional function to combine all results
        """
        self.results = []
        self.iteration_count = 0
        
        for i, item in enumerate(self.items):
            # Enforce iteration limit
            if self.max_iterations and i >= self.max_iterations:
                break
            
            try:
                result = transformer(item, i)
                self.results.append(result)
                self.iteration_count += 1
            except Exception as e:
                # Log but continue (fail-safe)
                self.results.append({"error": str(e), "item": str(item)})
        
        if aggregator:
            return aggregator(self.results)
        
        return self.results


class EnumeratedForLoop(Generic[T, R]):
    """
    For loop with automatic enumeration and tracking.
    Tracks: index, is_first, is_last, progress_percentage
    """
    
    def __init__(self, items: List[T]):
        self.items = items
        self.total = len(items)
    
    def execute(
        self,
        body: Callable[[T, dict], R],
        early_break: Callable[[R, dict], bool] = None
    ) -> List[R]:
        """
        Execute with automatic enumeration context.
        
        Provides context: index, is_first, is_last, progress, remaining
        """
        results = []
        
        for i, item in enumerate(self.items):
            context = {
                "index": i,
                "is_first": i == 0,
                "is_last": i == self.total - 1,
                "progress": (i + 1) / self.total if self.total > 0 else 0,
                "progress_percent": f"{((i + 1) / self.total * 100):.1f}%" if self.total > 0 else "0%",
                "remaining": self.total - i - 1,
                "total": self.total
            }
            
            try:
                result = body(item, context)
                results.append(result)
                
                # Early break if condition met
                if early_break and early_break(result, context):
                    break
                    
            except Exception as e:
                results.append({"error": str(e), "item_index": i})
        
        return results


# Example: Evaluate candidates with progress tracking
def evaluate_candidates(candidates: List[dict]) -> dict:
    """Evaluate multiple candidates with progress tracking."""
    
    loop = EnumeratedForLoop(candidates)
    
    results = loop.execute(
        body=lambda candidate, ctx: {
            **candidate,
            "evaluation_score": candidate.get("score", 0) * ctx["progress"],  # Weight by progress
            "position": f"{ctx['index'] + 1}/{ctx['total']}",
            "progress": ctx["progress_percent"]
        }
    )
    
    return {
        "evaluated": results,
        "total": len(candidates),
        "success_count": len([r for r in results if "error" not in r])
    }
```

---

### 1.3 While Loops (Condition-Controlled)

```python
# core/control_flow/while_loop.py
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
import time


@dataclass
class WhileLoopResult:
    """Result of while loop execution."""
    final_value: Any
    iterations: int
    converged: bool
    duration_ms: float
    history: List[Any]


class WhileLoop:
    """
    Implements while-loop with convergence detection and safety limits.
    
    Usage:
        loop = WhileLoop(
            initial_value=0.5,
            condition=lambda v, i: v < 0.95 and i < 100,
            body=lambda v, i: v + (1 - v) * 0.1  # Decay toward 1.0
        )
        result = loop.execute()
    """
    
    def __init__(
        self,
        initial_value: Any,
        condition: Callable[[Any, int], bool],
        body: Callable[[Any, int], Any]
    ):
        self.initial_value = initial_value
        self.condition = condition
        self.body = body
        self.max_iterations = 1000
        self.timeout_ms = 5000
        self.convergence_threshold: Optional[float] = None
    
    def with_max_iterations(self, max_iter: int) -> "WhileLoop":
        """Set maximum iterations."""
        self.max_iterations = max_iter
        return self
    
    def with_timeout(self, timeout_ms: int) -> "WhileLoop":
        """Set timeout in milliseconds."""
        self.timeout_ms = timeout_ms
        return self
    
    def with_convergence(self, threshold: float) -> "WhileLoop":
        """Set convergence detection (stop when delta < threshold)."""
        self.convergence_threshold = threshold
        return self
    
    def execute(self) -> WhileLoopResult:
        """Execute the while loop."""
        start_time = time.time()
        
        value = self.initial_value
        iterations = 0
        history = [value]
        converged = False
        
        while self.condition(value, iterations):
            if iterations >= self.max_iterations:
                break
            
            # Check timeout
            elapsed = (time.time() - start_time) * 1000
            if elapsed > self.timeout_ms:
                break
            
            # Execute body
            new_value = self.body(value, iterations)
            
            # Check convergence
            if self.convergence_threshold is not None:
                delta = abs(new_value - value)
                if delta < self.convergence_threshold:
                    converged = True
                    value = new_value
                    history.append(value)
                    break
            
            value = new_value
            history.append(value)
            iterations += 1
        
        duration_ms = (time.time() - start_time) * 1000
        
        return WhileLoopResult(
            final_value=value,
            iterations=iterations,
            converged=converged,
            duration_ms=duration_ms,
            history=history
        )


# Example: Optimize pattern score via iteration
def optimize_pattern_score(initial_score: float, target: float = 0.95) -> dict:
    """Optimize pattern score until convergence."""
    
    loop = WhileLoop(
        initial_value=initial_score,
        condition=lambda v, i: v < target and i < 100,
        body=lambda v, i: v + (target - v) * 0.2  # Decay toward target
    ).with_convergence(0.001).with_timeout(1000)
    
    result = loop.execute()
    
    return {
        "final_score": result.final_value,
        "iterations": result.iterations,
        "converged": result.converged,
        "duration_ms": result.duration_ms,
        "history": result.history
    }


# Example: Search until found
def search_with_while_loop(
    search_space: List[dict],
    predicate: Callable[[dict], bool]
) -> Optional[dict]:
    """Search through space until predicate is true."""
    
    loop = WhileLoop(
        initial_value=0,
        condition=lambda i, _: i < len(search_space),
        body=lambda i, _: i + 1
    )
    
    result = loop.execute()
    
    for i in range(len(search_space)):
        if predicate(search_space[i]):
            return search_space[i]
    
    return None
```

---

## Part 2: Deterministic Functions

### 2.1 Percentage Evaluation

```python
# core/control_flow/percentage.py
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import math


class PercentageMethod(str, Enum):
    """Methods for calculating percentages."""
    LINEAR = "linear"           # Direct percentage
    WEIGHTED = "weighted"       # Weighted by importance
    BAYESIAN = "bayesian"       # Bayesian average
    EXPONENTIAL = "exponential" # Exponential decay


@dataclass
class PercentageResult:
    """Result of percentage calculation."""
    value: float
    numerator: float
    denominator: float
    method: PercentageMethod
    confidence: float  # 0-1, based on sample size


class PercentageEvaluator:
    """
    Evaluate percentages with various methods and confidence.
    
    Usage:
        evaluator = PercentageEvaluator()
        
        # Simple percentage
        result = evaluator.evaluate(
            successes=45,
            total=100,
            method=PercentageMethod.LINEAR
        )
        
        # Weighted percentage
        result = evaluator.evaluate_weighted(
            items=[{"success": True, "weight": 1.0},
                   {"success": True, "weight": 2.0}],
            weight_fn=lambda x: x["weight"]
        )
    """
    
    def __init__(self, min_samples_for_confidence: int = 30):
        self.min_samples = min_samples_for_confidence
    
    def evaluate(
        self,
        successes: float,
        total: float,
        method: PercentageMethod = PercentageMethod.LINEAR
    ) -> PercentageResult:
        """Calculate percentage with specified method."""
        
        if total == 0:
            return PercentageResult(
                value=0.0,
                numerator=successes,
                denominator=total,
                method=method,
                confidence=0.0
            )
        
        if method == PercentageMethod.LINEAR:
            value = (successes / total) * 100
        
        elif method == PercentageMethod.BAYESIAN:
            # Bayesian average: (successes + prior*confidence) / (total + prior)
            prior = 0.5  # Assume 50% as prior
            value = ((successes + prior) / (total + 2 * prior)) * 100
        
        else:
            value = (successes / total) * 100
        
        # Calculate confidence based on sample size
        confidence = min(1.0, total / self.min_samples)
        
        return PercentageResult(
            value=round(value, 2),
            numerator=successes,
            denominator=total,
            method=method,
            confidence=confidence
        )
    
    def evaluate_weighted(
        self,
        items: List[Dict],
        success_fn: Callable[[Dict], bool],
        weight_fn: Callable[[Dict], float]
    ) -> PercentageResult:
        """Calculate weighted percentage."""
        
        total_weight = 0.0
        success_weight = 0.0
        
        for item in items:
            weight = weight_fn(item)
            total_weight += weight
            
            if success_fn(item):
                success_weight += weight
        
        return self.evaluate(
            successes=success_weight,
            total=total_weight,
            method=PercentageMethod.WEIGHTED
        )
    
    def evaluate_threshold(
        self,
        value: float,
        threshold: float,
        direction: str = "above"
    ) -> Dict[str, Any]:
        """
        Evaluate if value meets threshold.
        
        Returns deterministic result with reasoning.
        """
        
        if direction == "above":
            meets_threshold = value >= threshold
            margin = value - threshold
        else:
            meets_threshold = value <= threshold
            margin = threshold - value
        
        return {
            "value": value,
            "threshold": threshold,
            "direction": direction,
            "meets_threshold": meets_threshold,
            "margin": round(margin, 4),
            "percentage_of_threshold": round((value / threshold) * 100, 2) if threshold > 0 else 0,
            "verdict": "PASS" if meets_threshold else "FAIL"
        }


# Example: Pattern success rate evaluation
def evaluate_pattern_success_rate(
    pattern_id: str,
    executions: List[Dict]
) -> Dict[str, Any]:
    """Evaluate pattern success rate from execution history."""
    
    evaluator = PercentageEvaluator(min_samples_for_confidence=30)
    
    # Overall success rate
    successes = sum(1 for e in executions if e.get("outcome") == "success")
    total = len(executions)
    
    overall = evaluator.evaluate(successes, total)
    
    # By context
    by_context = {}
    contexts = set(e.get("context_type", "unknown") for e in executions)
    
    for ctx in contexts:
        ctx_executions = [e for e in executions if e.get("context_type") == ctx]
        ctx_successes = sum(1 for e in ctx_executions if e.get("outcome") == "success")
        by_context[ctx] = evaluator.evaluate(ctx_successes, len(ctx_executions))
    
    return {
        "pattern_id": pattern_id,
        "overall_rate": overall.value,
        "confidence": overall.confidence,
        "sample_size": total,
        "by_context": {k: v.value for k, v in by_context.items()},
        "verdict": "RELIABLE" if overall.confidence >= 0.8 else "NEEDS_DATA"
    }
```

---

### 2.2 Counter with Bounds

```python
# core/control_flow/counter.py
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class CounterStrategy(str, Enum):
    """Strategies for counter behavior at bounds."""
    STOP = "stop"           # Stop at bounds
    WRAP = "wrap"           # Wrap around (modulo)
    CLAMP = "clamp"         # Clamp to bounds
    BOUNCE = "bounce"       # Bounce between bounds


@dataclass
class Counter:
    """
    Bounded counter with configurable behavior.
    
    Usage:
        counter = Counter(initial=0, min=0, max=100, strategy=CounterStrategy.CLAMP)
        counter.increment()  # 1
        counter.increment(5)  # 6
        counter.decrement(10)  # 0 (clamped)
    """
    
    value: int
    min_value: int = 0
    max_value: int = 100
    strategy: CounterStrategy = CounterStrategy.CLAMP
    increment_count: int = 0
    decrement_count: int = 0
    reset_count: int = 0
    
    def increment(self, amount: int = 1) -> int:
        """Increment counter, respecting strategy."""
        self.increment_count += 1
        
        new_value = self.value + amount
        
        if new_value > self.max_value:
            if self.strategy == CounterStrategy.STOP:
                return self.value
            elif self.strategy == CounterStrategy.WRAP:
                self.value = self.min_value + (new_value - self.max_value - 1)
            elif self.strategy == CounterStrategy.CLAMP:
                self.value = self.max_value
            elif self.strategy == CounterStrategy.BOUNCE:
                # Bounce: go back down
                overshoot = new_value - self.max_value
                self.value = self.max_value - overshoot
        else:
            self.value = new_value
        
        return self.value
    
    def decrement(self, amount: int = 1) -> int:
        """Decrement counter, respecting strategy."""
        self.decrement_count += 1
        
        new_value = self.value - amount
        
        if new_value < self.min_value:
            if self.strategy == CounterStrategy.STOP:
                return self.value
            elif self.strategy == CounterStrategy.WRAP:
                self.value = self.max_value - (self.min_value - new_value - 1)
            elif self.strategy == CounterStrategy.CLAMP:
                self.value = self.min_value
            elif self.strategy == CounterStrategy.BOUNCE:
                undershoot = self.min_value - new_value
                self.value = self.min_value + undershoot
        else:
            self.value = new_value
        
        return self.value
    
    def reset(self, value: Optional[int] = None) -> int:
        """Reset counter to initial or specified value."""
        self.reset_count += 1
        self.value = value if value is not None else self.min_value
        return self.value
    
    def get_state(self) -> dict:
        """Get full counter state."""
        return {
            "value": self.value,
            "min": self.min_value,
            "max": self.max_value,
            "strategy": self.strategy.value,
            "total_increments": self.increment_count,
            "total_decrements": self.decrement_count,
            "total_resets": self.reset_count,
            "utilization": (self.value - self.min_value) / (self.max_value - self.min_value) if self.max_value > self.min_value else 0
        }


class AdaptiveCounter(Counter):
    """
    Counter that adapts its bounds based on usage patterns.
    
    Tracks usage and can auto-expand or auto-shrink bounds.
    """
    
    def __init__(self, *args, auto_expand_threshold: float = 0.9, auto_shrink_threshold: float = 0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_expand_threshold = auto_expand_threshold
        self.auto_shrink_threshold = auto_shrink_threshold
        self.expansion_count = 0
        self.shrink_count = 0
    
    def _check_bounds_adjustment(self):
        """Check if bounds need adjustment."""
        utilization = self.get_state()["utilization"]
        
        if utilization >= self.auto_expand_threshold:
            # Expand bounds
            old_max = self.max_value
            self.max_value = int(self.max_value * 1.5)
            self.expansion_count += 1
        
        elif utilization <= self.auto_shrink_threshold and self.max_value > 100:
            # Shrink bounds
            self.max_value = int(self.max_value * 0.8)
            self.shrink_count += 1
```

---

## Part 3: Prompts for Control Flow Adaptation

### 3.1 If/Else Pattern Prompts

```
## Prompt: Adapt If/Else to Problem

Given a problem description, generate an if/else control flow structure:

**Input:**
- Problem: {describe the decision problem}
- Conditions: {list the conditions to check}
- Actions: {list corresponding actions}

**Template:**
```
def solve_{problem_name}(context: dict) -> dict:
    """
    {One-line description of the decision logic}
    """
    
    if_else = IfElseControlFlow()
    
    # Condition 1: {description}
    if_else.when(
        lambda c: {condition_1_expression},
        lambda c: {{"action": "{action_1}", "reason": "{reason_1}"}}
    )
    
    # Condition 2: {description}
    if_else.when(
        lambda c: {condition_2_expression},
        lambda c: {{"action": "{action_2}", "reason": "{reason_2}"}}
    )
    
    # Default case
    if_else.otherwise(
        lambda c: {{"action": "{default_action}", "reason": "{default_reason}"}}
    )
    
    return if_else.execute(context)
```

**Example:**
- Problem: Route pattern by danger level
- Conditions: danger >= 0.8, danger >= 0.5, danger >= 0.2
- Actions: BLOCK, VERIFY, LOG, APPROVE
```

---

### 3.2 For Loop Pattern Prompts

```
## Prompt: Adapt For Loop to Problem

Given a collection of items to process, generate a for loop with proper tracking:

**Input:**
- Items: {what are we iterating over?}
- Transformation: {what to do with each item?}
- Aggregation: {how to combine results?}
- Safety limits: {max iterations? timeout?}

**Template:**
```
def process_{items_name}(
    items: List[{item_type}],
    max_items: int = {default_limit}
) -> {return_type}:
    """
    {Description}
    """
    
    if not items:
        return {empty_result}
    
    loop = EnumeratedForLoop(items)
    
    results = loop.execute(
        body=lambda item, ctx: {transformation_code},
        early_break=lambda result, ctx: {early_break_condition}
    )
    
    return {aggregator_code}
```

**Example:**
- Items: List of candidate patterns
- Transformation: Evaluate score and confidence
- Aggregation: Return top-K by score
```

---

### 3.3 While Loop Pattern Prompts

```
## Prompt: Adapt While Loop to Problem

Given an iterative optimization or search problem, generate a bounded while loop:

**Input:**
- Initial value: {starting point}
- Termination condition: {when to stop?}
- Update function: {how to progress toward solution?}
- Safety bounds: {max iterations? timeout? convergence?}

**Template:**
```
def optimize_{problem_name}(
    initial_value: {initial_type},
    target: {target_type} = {target_value}
) -> {result_type}:
    """
    {Description of optimization}
    """
    
    loop = WhileLoop(
        initial_value=initial_value,
        condition=lambda v, i: {termination_condition},
        body=lambda v, i: {update_expression}
    ).with_max_iterations({max_iter}).with_timeout({timeout_ms}).with_convergence({threshold})
    
    result = loop.execute()
    
    return {{
        "value": result.final_value,
        "iterations": result.iterations,
        "converged": result.converged,
        "duration_ms": result.duration_ms
    }}
```

**Example:**
- Initial value: 0.0
- Target: 0.95
- Condition: value < target
- Body: value + (target - value) * 0.1
```

---

### 3.4 Percentage Evaluation Prompts

```
## Prompt: Adapt Percentage Evaluation to Problem

Given success/failure data, generate percentage evaluation code:

**Input:**
- Success criteria: {what defines success?}
- Weighting: {any weights for different items?}
- Confidence threshold: {minimum samples for reliable result?}

**Template:**
```
def evaluate_{metric_name}(
    executions: List[{execution_type}]
) -> {result_type}:
    """
    {Description}
    """
    
    evaluator = PercentageEvaluator(min_samples_for_confidence={min_samples})
    
    # Simple evaluation
    successes = sum(1 for e in executions if {success_condition})
    result = evaluator.evaluate(successes, len(executions))
    
    # Threshold check
    threshold_result = evaluator.evaluate_threshold(
        result.value,
        threshold={threshold_value},
        direction="{above_or_below}"
    )
    
    return {{
        "percentage": result.value,
        "confidence": result.confidence,
        "sample_size": len(executions),
        "meets_threshold": threshold_result["meets_threshold"],
        "verdict": "PASS" if threshold_result["meets_threshold"] and result.confidence >= 0.8 else "FAIL"
    }}
```

---

## Part 4: Complete Examples

### Example 1: Pattern Ranking with All Control Flow Types

```python
# Complete example: Rank patterns using branching, loops, and percentage

def rank_patterns_for_context(
    patterns: List[dict],
    context: dict,
    max_candidates: int = 10
) -> dict:
    """
    Complete pattern ranking using if/else, for loops, and percentage evaluation.
    """
    
    # STEP 1: Filter with if/else (branching)
    filtered = []
    
    for_loop = EnumeratedForLoop(patterns)
    filtered = for_loop.execute(
        body=lambda p, ctx: {
            **p,
            "include": p.get("score", 0) >= 0.1 and p.get("domain") == context.get("domain")
        }
    )
    patterns_to_rank = [p for p in filtered if p.get("include")]
    
    # STEP 2: Evaluate each with percentage
    evaluator = PercentageEvaluator(min_samples_for_confidence=30)
    ranked = []
    
    for pattern in patterns_to_rank:
        # Calculate success rate from history
        history = pattern.get("execution_history", [])
        success_result = evaluator.evaluate(
            successes=sum(1 for h in history if h.get("outcome") == "success"),
            total=len(history)
        )
        
        # Determine action via if/else
        if_else = IfElseControlFlow()
        
        if_else.when(
            lambda c: c["confidence"] >= 0.8 and c["success_rate"] >= 80,
            lambda c: {**c, "tier": "HIGH", "action": "recommend"}
        )
        
        if_else.when(
            lambda c: c["confidence"] >= 0.5 and c["success_rate"] >= 50,
            lambda c: {**c, "tier": "MEDIUM", "action": "consider"}
        )
        
        if_else.otherwise(
            lambda c: {**c, "tier": "LOW", "action": "experimental"}
        )
        
        decision = if_else.execute({
            "confidence": success_result.confidence,
            "success_rate": success_result.value,
            "pattern": pattern
        })
        
        ranked.append({
            **pattern,
            "success_rate": success_result.value,
            "confidence": success_result.confidence,
            "tier": decision["tier"],
            "action": decision["action"]
        })
    
    # STEP 3: Sort and limit (for loop with aggregation)
    ranked.sort(key=lambda p: (p["success_rate"], p["confidence"]), reverse=True)
    
    return {
        "ranked_patterns": ranked[:max_candidates],
        "total_evaluated": len(ranked),
        "high_confidence_count": len([p for p in ranked if p["confidence"] >= 0.8])
    }
```

### Example 2: Iterative Score Optimization

```python
def optimize_confidence_score(
    initial_confidence: float,
    target_confidence: float = 0.95,
    decay_rate: float = 0.1
) -> dict:
    """
    Optimize confidence score using while loop with convergence.
    """
    
    loop = WhileLoop(
        initial_value=initial_confidence,
        condition=lambda v, i: v < target_confidence and i < 100,
        body=lambda v, i: v + (target_confidence - v) * decay_rate
    ).with_convergence(0.001).with_timeout(5000)
    
    result = loop.execute()
    
    return {
        "final_confidence": result.final_value,
        "iterations": result.iterations,
        "converged": result.converged,
        "history": result.history,
        "duration_ms": result.duration_ms
    }


# Example usage
result = optimize_confidence_score(0.3, target_confidence=0.95)
# Output: {"final_confidence": 0.949, "iterations": 42, "converged": True, ...}
```

---

## Implementation Checklist

- [ ] IfElseControlFlow with condition evaluation
- [ ] ForLoop with iteration limits
- [ ] EnumeratedForLoop with progress tracking
- [ ] WhileLoop with convergence detection
- [ ] PercentageEvaluator with multiple methods
- [ ] Counter with bounded strategies
- [ ] Prompt templates for each control flow type
- [ ] Complete examples with branching + loops + percentages
- [ ] Unit tests for all primitives

---

## Part 5: Composed Control Flow Patterns

### 5.1 Switch/Match Statement

```python
# core/control_flow/switch.py
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class MatchResult(Enum):
    """Result of pattern matching."""
    MATCHED = "matched"
    NO_MATCH = "no_match"
    FALLTHROUGH = "fallthrough"


@dataclass
class Case:
    """A case in switch/match logic."""
    pattern: Any  # Can be value, regex, or callable
    action: Callable[[Any], Any]
    is_default: bool = False


class SwitchMatch:
    """
    Implements switch/match control flow with multiple matching strategies.
    
    Usage:
        switch = SwitchMatch(key="status")
        switch.case("active", lambda x: activate(x))
        switch.case("pending", lambda x: notify(x))
        switch.case(lambda x: x > 10, lambda x: handle_high(x))  # Predicate
        switch.default(lambda x: unknown(x))
        result = switch.evaluate({"status": "active"})
    """
    
    def __init__(self, key: str = None):
        self.key = key
        self.cases: List[Case] = []
        self.default_case: Optional[Case] = None
    
    def case(self, pattern: Any, action: Callable[[Any], Any]) -> "SwitchMatch":
        """Add a case with exact match or predicate."""
        case = Case(
            pattern=pattern,
            action=action,
            is_default=False
        )
        self.cases.append(case)
        return self
    
    def case_predicate(self, predicate: Callable[[Any], bool], action: Callable[[Any], Any]) -> "SwitchMatch":
        """Add a case with predicate matching."""
        case = Case(
            pattern=predicate,  # Store predicate as pattern
            action=action,
            is_default=False
        )
        self.cases.append(case)
        return self
    
    def default(self, action: Callable[[Any], Any]) -> "SwitchMatch":
        """Add default case (executed when no match found)."""
        self.default_case = Case(
            pattern=None,
            action=action,
            is_default=True
        )
        return self
    
    def evaluate(self, value: Any) -> Any:
        """Evaluate switch/match against value."""
        # Get value if key specified
        target = value.get(self.key, value) if self.key else value
        
        for case in self.cases:
            matched = False
            
            if callable(case.pattern):
                # Predicate match
                try:
                    matched = case.pattern(target)
                except:
                    matched = False
            else:
                # Exact match
                matched = case.pattern == target
            
            if matched:
                return case.action(target)
        
        # Default case
        if self.default_case:
            return self.default_case.action(target)
        
        return None


class PatternSwitch:
    """Specialized switch for pattern type routing."""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.default_handler: Optional[Callable] = None
    
    def on_pattern(self, pattern_type: str) -> Callable:
        """Decorator to register pattern handler."""
        def decorator(func: Callable) -> Callable:
            self.handlers[pattern_type] = func
            return func
        return decorator
    
    def on_default(self, func: Callable) -> Callable:
        """Register default handler."""
        self.default_handler = func
        return func
    
    def dispatch(self, pattern: dict) -> Any:
        """Dispatch to appropriate handler."""
        pattern_type = pattern.get("pattern_type", "unknown")
        
        handler = self.handlers.get(pattern_type, self.default_handler)
        
        if handler:
            return handler(pattern)
        
        raise ValueError(f"No handler for pattern type: {pattern_type}")
```

### 5.2 Try/Catch/Finally

```python
# core/control_flow/exception_handling.py
from typing import Callable, Any, Optional, List, Type
from dataclasses import dataclass
from enum import Enum
import traceback


class ExceptionSeverity(Enum):
    """Severity of caught exception."""
    LOW = "low"       # Log and continue
    MEDIUM = "medium" # Retry with fallback
    HIGH = "high"     # Block execution


@dataclass
class ExceptionHandler:
    """Handler for specific exception type."""
    exception_type: Type[Exception]
    severity: ExceptionSeverity
    action: Callable[[Exception], Any]
    retry_count: int = 0


class TryCatchFinally:
    """
    Implements try/catch/finally with retry and fallback logic.
    
    Usage:
        result = TryCatchFinally()
            .try(lambda: risky_operation())
            .catch(ValueError, severity=HIGH, action=handle_value_error)
            .catch(TimeoutError, severity=MEDIUM, action=retry_with_fallback)
            .finally(lambda: cleanup())
            .execute()
    """
    
    def __init__(self):
        self.try_block: Optional[Callable] = None
        self.catch_blocks: List[ExceptionHandler] = []
        self.finally_block: Optional[Callable] = None
        self.result: Any = None
        self.error: Optional[Exception] = None
    
    def try_block(self, func: Callable) -> "TryCatchFinally":
        """Set the try block."""
        self.try_block = func
        return self
    
    def catch(
        self,
        exception_type: Type[Exception],
        severity: ExceptionSeverity = ExceptionSeverity.MEDIUM,
        action: Callable[[Exception], Any] = None,
        retry_count: int = 0
    ) -> "TryCatchFinally":
        """Add catch block for specific exception."""
        handler = ExceptionHandler(
            exception_type=exception_type,
            severity=severity,
            action=action or (lambda e: None),
            retry_count=retry_count
        )
        self.catch_blocks.append(handler)
        return self
    
    def finally_block(self, func: Callable) -> "TryCatchFinally":
        """Set finally block (always executes)."""
        self.finally_block = func
        return self
    
    def execute(self) -> Any:
        """Execute try/catch/finally with retry logic."""
        try:
            # Execute try block
            if self.try_block:
                self.result = self.try_block()
            
        except Exception as e:
            self.error = e
            
            # Find matching catch block
            for handler in self.catch_blocks:
                if isinstance(e, handler.exception_type):
                    # Retry logic
                    for attempt in range(handler.retry_count + 1):
                        try:
                            if attempt > 0:
                                # Retry attempt
                                self.result = self.try_block()
                                self.error = None  # Clear error on success
                                break
                            else:
                                # First attempt already failed, try again
                                self.result = self.try_block()
                                self.error = None
                                break
                        except Exception as retry_error:
                            if attempt == handler.retry_count:
                                # Last attempt failed, execute catch action
                                self.result = handler.action(retry_error)
            
            # No matching catch - re-raise
            if self.error:
                raise self.error
        
        finally:
            # Execute finally block
            if self.finally_block:
                self.finally_block()
        
        return self.result


# Example: Safe pattern execution with retries
def execute_pattern_safely(pattern: dict, context: dict) -> dict:
    """Execute pattern with error handling."""
    
    return TryCatchFinally()\
        .try_block(lambda: run_pattern(pattern, context))\
        .catch(TimeoutError, severity=ExceptionSeverity.MEDIUM, 
               action=lambda e: {"status": "timeout", "error": str(e)}, retry_count=2)\
        .catch(ValueError, severity=ExceptionSeverity.HIGH,
               action=lambda e: {"status": "invalid_input", "error": str(e)})\
        .catch(Exception, severity=ExceptionSeverity.LOW,
               action=lambda e: {"status": "error", "error": str(e)})\
        .finally_block(lambda: cleanup_resources())\
        .execute()
```

### 5.3 Pipeline Pattern

```python
# core/control_flow/pipeline.py
from typing import Callable, Any, List, Optional, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum


T = TypeVar('T')
R = TypeVar('R')


class PipelineStage(Generic[T, R]):
    """A stage in a processing pipeline."""
    name: str
    transform: Callable[[T], R]
    condition: Optional[Callable[[T], bool]] = None  # Skip if false
    
    def process(self, input_data: T) -> Optional[R]:
        """Process input through this stage."""
        # Check condition
        if self.condition and not self.condition(input_data):
            return None
        
        return self.transform(input_data)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    output: Any
    stages_executed: List[str]
    stages_skipped: List[str]
    errors: List[dict]
    duration_ms: float


class Pipeline(Generic[T, R]):
    """
    Implements pipeline control flow (function composition).
    
    Usage:
        pipeline = Pipeline()
        pipeline.stage("validate", validate_input)
        pipeline.stage("transform", transform_data)
        pipeline.stage("enrich", enrich_data)
        pipeline.stage("save", save_to_db, condition=lambda x: x.get("valid"))
        
        result = pipeline.execute(input_data)
    """
    
    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.stages: List[PipelineStage] = []
    
    def stage(
        self,
        name: str,
        transform: Callable[[Any], Any],
        condition: Optional[Callable[[Any], bool]] = None
    ) -> "Pipeline":
        """Add a stage to the pipeline."""
        stage = PipelineStage(
            name=name,
            transform=transform,
            condition=condition
        )
        self.stages.append(stage)
        return self
    
    def execute(self, input_data: T) -> PipelineResult:
        """Execute all stages in sequence."""
        import time
        start_time = time.time()
        
        current = input_data
        stages_executed = []
        stages_skipped = []
        errors = []
        
        for stage in self.stages:
            try:
                # Check condition
                if stage.condition and not stage.condition(current):
                    stages_skipped.append(stage.name)
                    continue
                
                # Execute stage
                result = stage.process(current)
                current = result
                stages_executed.append(stage.name)
                
            except Exception as e:
                errors.append({
                    "stage": stage.name,
                    "error": str(e),
                    "stage_index": len(stages_executed)
                })
                # Continue or break based on error handling
                # For now, continue pipeline
        
        duration_ms = (time.time() - start_time) * 1000
        
        return PipelineResult(
            output=current,
            stages_executed=stages_executed,
            stages_skipped=stages_skipped,
            errors=errors,
            duration_ms=duration_ms
        )


# Example: Pattern processing pipeline
def create_pattern_pipeline() -> Pipeline:
    """Create pattern processing pipeline."""
    
    pipeline = Pipeline(name="pattern_processing")
    
    # Stage 1: Validate input
    pipeline.stage(
        "validate",
        transform=lambda p: validate_pattern(p),
        condition=lambda x: x is not None
    )
    
    # Stage 2: Extract features
    pipeline.stage(
        "extract_features",
        transform=lambda p: extract_pattern_features(p)
    )
    
    # Stage 3: Classify domain
    pipeline.stage(
        "classify_domain",
        transform=lambda p: classify_pattern_domain(p)
    )
    
    # Stage 4: Generate embeddings (only if enabled)
    pipeline.stage(
        "generate_embedding",
        transform=lambda p: generate_pattern_embedding(p),
        condition=lambda p: p.get("generate_embedding", False)
    )
    
    # Stage 5: Save to storage
    pipeline.stage(
        "save",
        transform=lambda p: save_pattern(p),
        condition=lambda p: p.get("valid", False)
    )
    
    return pipeline
```

---

## Part 6: Control Flow for Pattern Detection

### 6.1 Pattern Detection via Control Flow Analysis

```python
# core/control_flow/pattern_detection.py
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class ControlFlowNodeType(Enum):
    """Types of control flow nodes."""
    IF = "if"
    ELSE = "else"
    FOR = "for"
    WHILE = "while"
    SWITCH = "switch"
    TRY = "try"
    CALL = "call"  # Function call
    RETURN = "return"
    YIELD = "yield"


@dataclass
class ControlFlowNode:
    """A node in the control flow graph."""
    node_type: ControlFlowNodeType
    line_number: int
    content: str
    children: List["ControlFlowNode"] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class ControlFlowDetector:
    """
    Detect control flow patterns in code/traces.
    
    Maps textual reasoning to control flow structures.
    """
    
    # Keywords that indicate control flow
    IF_KEYWORDS = ["if", "when", "check", "verify", "should", "conditionally"]
    ELSE_KEYWORDS = ["else", "otherwise", "otherwise", "fallback", "default"]
    FOR_KEYWORDS = ["for each", "iterate", "loop", "over", "through"]
    WHILE_KEYWORDS = ["until", "while", "repeat", "continue until"]
    SWITCH_KEYWORDS = ["switch", "match", "case", "based on", "depending on"]
    
    def detect_from_text(self, text: str) -> List[ControlFlowNode]:
        """Detect control flow from natural language text."""
        nodes = []
        lines = text.split("\n")
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower().strip()
            
            # Detect if statements
            if any(kw in line_lower for kw in self.IF_KEYWORDS):
                if "?" in line or "if " in line_lower or "should " in line_lower:
                    nodes.append(ControlFlowNode(
                        node_type=ControlFlowNodeType.IF,
                        line_number=i,
                        content=line.strip()
                    ))
            
            # Detect else statements
            elif any(kw in line_lower for kw in self.ELSE_KEYWORDS):
                nodes.append(ControlFlowNode(
                    node_type=ControlFlowNodeType.ELSE,
                    line_number=i,
                    content=line.strip()
                ))
            
            # Detect loops
            elif any(kw in line_lower for kw in self.FOR_KEYWORDS):
                nodes.append(ControlFlowNode(
                    node_type=ControlFlowNodeType.FOR,
                    line_number=i,
                    content=line.strip()
                ))
            
            elif any(kw in line_lower for kw in self.WHILE_KEYWORDS):
                nodes.append(ControlFlowNode(
                    node_type=ControlFlowNodeType.WHILE,
                    line_number=i,
                    content=line.strip()
                ))
            
            # Detect switch/match
            elif any(kw in line_lower for kw in self.SWITCH_KEYWORDS):
                nodes.append(ControlFlowNode(
                    node_type=ControlFlowNodeType.SWITCH,
                    line_number=i,
                    content=line.strip()
                ))
        
        return nodes
    
    def detect_from_code(self, code: str) -> List[ControlFlowNode]:
        """Detect control flow from Python code."""
        import ast
        
        nodes = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    nodes.append(ControlFlowNode(
                        node_type=ControlFlowNodeType.IF,
                        line_number=node.lineno,
                        content=ast.unparse(node.test) if hasattr(ast, 'unparse') else "if condition"
                    ))
                
                elif isinstance(node, ast.For):
                    nodes.append(ControlFlowNode(
                        node_type=ControlFlowNodeType.FOR,
                        line_number=node.lineno,
                        content=f"for {ast.dump(node.target)} in ..."
                    ))
                
                elif isinstance(node, ast.While):
                    nodes.append(ControlFlowNode(
                        node_type=ControlFlowNodeType.WHILE,
                        line_number=node.lineno,
                        content="while ..."
                    ))
                
                elif isinstance(node, (ast.Try, ast.ExceptHandler)):
                    nodes.append(ControlFlowNode(
                        node_type=ControlFlowNodeType.TRY,
                        line_number=node.lineno if hasattr(node, 'lineno') else 0,
                        content="try/except"
                    ))
        
        except SyntaxError:
            pass
        
        return nodes


# Example: Analyze reasoning trace for control flow
def analyze_reasoning_trace(trace: str) -> dict:
    """Analyze reasoning trace to extract control flow pattern."""
    
    detector = ControlFlowDetector()
    
    # Try to detect from code first, then text
    nodes = detector.detect_from_code(trace)
    if not nodes:
        nodes = detector.detect_from_text(trace)
    
    # Count control flow types
    from collections import Counter
    type_counts = Counter(n.node_type.value for n in nodes)
    
    return {
        "total_nodes": len(nodes),
        "control_flow_types": dict(type_counts),
        "has_conditionals": ControlFlowNodeType.IF in [n.node_type for n in nodes],
        "has_loops": any(n.node_type in [ControlFlowNodeType.FOR, ControlFlowNodeType.WHILE] for n in nodes),
        "has_error_handling": ControlFlowNodeType.TRY in [n.node_type for n in nodes],
        "complexity_score": len(nodes) + type_counts.get("if", 0) * 2 + type_counts.get("for", 0) * 2
    }
```

### 6.2 Enforce Loop Bounds

```python
# core/control_flow/loop_enforcer.py
from typing import Callable, Any, List, Optional, TypeVar
from dataclasses import dataclass
import time


T = TypeVar('T')


@dataclass
class LoopEnforcementResult:
    """Result of enforced loop execution."""
    results: List[Any]
    iterations: int
    terminated: str  # "max_iterations", "timeout", "condition", "exhausted"
    duration_ms: float


class LoopEnforcer:
    """
    Enforce safety bounds on any loop operation.
    
    Prevents infinite loops, timeout issues, and resource exhaustion.
    """
    
    def __init__(
        self,
        max_iterations: int = 1000,
        timeout_ms: int = 5000,
        max_results: int = 10000
    ):
        self.max_iterations = max_iterations
        self.timeout_ms = timeout_ms
        self.max_results = max_results
    
    def enforce_for_loop(
        self,
        items: List[T],
        body: Callable[[T, int], Any]
    ) -> LoopEnforcementResult:
        """Execute for loop with enforced bounds."""
        start_time = time.time()
        results = []
        
        # Check item count
        if len(items) > self.max_iterations:
            items = items[:self.max_iterations]
        
        for i, item in enumerate(items):
            # Check timeout
            elapsed = (time.time() - start_time) * 1000
            if elapsed > self.timeout_ms:
                return LoopEnforcementResult(
                    results=results,
                    iterations=i,
                    terminated="timeout",
                    duration_ms=elapsed
                )
            
            # Check result limit
            if len(results) >= self.max_results:
                return LoopEnforcementResult(
                    results=results,
                    iterations=i,
                    terminated="max_results",
                    duration_ms=elapsed
                )
            
            # Execute body
            try:
                result = body(item, i)
                results.append(result)
            except Exception as e:
                # Log but continue
                results.append({"error": str(e), "index": i})
        
        return LoopEnforcementResult(
            results=results,
            iterations=len(items),
            terminated="exhausted",
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def enforce_while_loop(
        self,
        condition: Callable[[int, Any], bool],
        body: Callable[[int], Any],
        initial_value: Any = None
    ) -> LoopEnforcementResult:
        """Execute while loop with enforced bounds."""
        start_time = time.time()
        results = []
        value = initial_value
        i = 0
        
        while condition(i, value):
            # Check max iterations
            if i >= self.max_iterations:
                return LoopEnforcementResult(
                    results=results,
                    iterations=i,
                    terminated="max_iterations",
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Check timeout
            elapsed = (time.time() - start_time) * 1000
            if elapsed > self.timeout_ms:
                return LoopEnforcementResult(
                    results=results,
                    iterations=i,
                    terminated="timeout",
                    duration_ms=elapsed
                )
            
            # Execute body
            try:
                value = body(i)
                results.append(value)
            except Exception as e:
                results.append({"error": str(e), "iteration": i})
            
            i += 1
        
        return LoopEnforcementResult(
            results=results,
            iterations=i,
            terminated="condition",
            duration_ms=(time.time() - start_time) * 1000
        )


# Example: Safe pattern iteration
def iterate_patterns_safely(
    patterns: List[dict],
    processor: Callable[[dict], dict]
) -> dict:
    """Iterate over patterns with safety enforcement."""
    
    enforcer = LoopEnforcer(max_iterations=100, timeout_ms=5000)
    
    result = enforcer.enforce_for_loop(
        items=patterns,
        body=lambda p, i: processor(p)
    )
    
    return {
        "processed": len(result.results),
        "total_iterations": result.iterations,
        "terminated": result.terminated,
        "duration_ms": result.duration_ms,
        "success_count": len([r for r in result.results if "error" not in r])
    }
```

---

## Part 7: Testing Control Flow

### 7.1 Property-Based Testing

```python
# tests/unit/test_control_flow.py
import pytest
from hypothesis import given, strategies as st, settings


class TestIfElseControlFlow:
    """Property-based tests for if/else control flow."""
    
    @given(score=st.floats(min_value=0, max_value=1))
    @settings(max_examples=100)
    def test_branching_covers_all_cases(self, score):
        """Every score value should match exactly one branch."""
        
        branches_matched = []
        
        if_else = IfElseControlFlow()
        
        if_else.when(
            lambda c: c["score"] >= 0.8,
            lambda c: branches_matched.append("high")
        )
        if_else.when(
            lambda c: 0.5 <= c["score"] < 0.8,
            lambda c: branches_matched.append("medium")
        )
        if_else.when(
            lambda c: 0.2 <= c["score"] < 0.5,
            lambda c: branches_matched.append("low")
        )
        if_else.otherwise(
            lambda c: branches_matched.append("minimal")
        )
        
        result = if_else.execute({"score": score})
        
        # Should match exactly one branch
        assert len(branches_matched) == 1
    
    def test_empty_branches_returns_unchanged(self):
        """No branches should return original context."""
        if_else = IfElseControlFlow()
        result = if_else.execute({"value": 42})
        assert result == {"value": 42}


class TestWhileLoop:
    """Tests for while loop convergence."""
    
    def test_convergence_detection(self):
        """Should detect convergence when delta is small."""
        
        loop = WhileLoop(
            initial_value=0.0,
            condition=lambda v, i: v < 0.99,
            body=lambda v, i: v + (1 - v) * 0.1
        ).with_convergence(0.001)
        
        result = loop.execute()
        
        # Should converge
        assert result.converged is True
        assert result.final_value >= 0.99 - 0.001
    
    def test_max_iterations_prevents_infinite_loop(self):
        """Should stop at max iterations."""
        
        call_count = [0]
        
        loop = WhileLoop(
            initial_value=0.0,
            condition=lambda v, i: i < 1000000,  # Would run forever
            body=lambda v, i: (call_count.__iadd__(1), v + 1)[1]
        ).with_max_iterations(100)
        
        result = loop.execute()
        
        assert result.iterations == 100
        assert call_count[0] == 100
    
    def test_timeout_prevents_long_running(self):
        """Should stop at timeout."""
        
        import time
        
        loop = WhileLoop(
            initial_value=0,
            condition=lambda v, i: True,  # Run forever
            body=lambda v, i: (time.sleep(0.1), v + 1)[1]
        ).with_timeout(250)  # 250ms timeout
        
        result = loop.execute()
        
        # Should stop before 10 iterations (each takes 100ms)
        assert result.iterations < 10


class TestPercentageEvaluator:
    """Tests for percentage evaluation."""
    
    def test_zero_denominator_returns_zero(self):
        """Zero denominator should return 0 with zero confidence."""
        
        evaluator = PercentageEvaluator()
        result = evaluator.evaluate(5, 0)
        
        assert result.value == 0.0
        assert result.confidence == 0.0
    
    def test_bayesian_average_moves_toward_50(self):
        """Bayesian average should shrink toward 0.5 with small samples."""
        
        evaluator = PercentageEvaluator()
        
        # With 1 success out of 1 (100%), Bayesian should be less extreme
        bayesian = evaluator.evaluate(1, 1, method=PercentageMethod.BAYESIAN)
        
        # Bayesian should be less than 100%
        assert bayesian.value < 100.0
    
    @given(successes=st.integers(min_value=0, max_value=100),
           total=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_confidence_increases_with_sample_size(self, successes, total):
        """Confidence should increase with more samples."""
        
        evaluator = PercentageEvaluator(min_samples_for_confidence=30)
        result = evaluator.evaluate(successes, total)
        
        # If total >= 30, confidence should be >= 1.0
        if total >= 30:
            assert result.confidence == 1.0


class TestLoopEnforcer:
    """Tests for loop enforcement."""
    
    def test_enforces_max_iterations(self):
        """Should stop at max_iterations."""
        
        enforcer = LoopEnforcer(max_iterations=10)
        
        result = enforcer.enforce_for_loop(
            items=list(range(100)),
            body=lambda x, i: x * 2
        )
        
        assert result.iterations == 10
        assert len(result.results) == 10
    
    def test_enforces_timeout(self):
        """Should stop at timeout."""
        
        import time
        
        enforcer = LoopEnforcer(timeout_ms=100)
        
        result = enforcer.enforce_while_loop(
            condition=lambda i, v: True,
            body=lambda i: (time.sleep(0.05), i + 1)[1],
            initial_value=0
        )
        
        # Should stop before 10 iterations (500ms total)
        assert result.iterations < 10
        assert result.terminated == "timeout"
```

---

## Part 8: Extension Points

### 8.1 Custom Control Flow Patterns

```python
# core/control_flow/extensions.py
from typing import Callable, Any, List, Dict
from dataclasses import dataclass


class ControlFlowBuilder:
    """
    Builder for composing custom control flow patterns.
    """
    
    def __init__(self):
        self.primitives: List[Dict[str, Any]] = []
    
    def add_branch(self, condition: Callable, action: Callable) -> "ControlFlowBuilder":
        """Add a branch primitive."""
        self.primitives.append({
            "type": "branch",
            "condition": condition,
            "action": action
        })
        return self
    
    def add_loop(
        self,
        condition: Callable,
        body: Callable,
        max_iterations: int = None
    ) -> "ControlFlowBuilder":
        """Add a loop primitive."""
        self.primitives.append({
            "type": "loop",
            "condition": condition,
            "body": body,
            "max_iterations": max_iterations
        })
        return self
    
    def add_transform(self, transform: Callable) -> "ControlFlowBuilder":
        """Add a transformation primitive."""
        self.primitives.append({
            "type": "transform",
            "function": transform
        })
        return self
    
    def build(self) -> Callable[[Any], Any]:
        """Build the composed control flow."""
        
        def composed(input_data: Any) -> Any:
            current = input_data
            
            for primitive in self.primitives:
                if primitive["type"] == "branch":
                    if primitive["condition"](current):
                        current = primitive["action"](current)
                
                elif primitive["type"] == "loop":
                    iterations = 0
                    max_iter = primitive.get("max_iterations", 1000)
                    
                    while primitive["condition"](current) and iterations < max_iter:
                        current = primitive["body"](current)
                        iterations += 1
                
                elif primitive["type"] == "transform":
                    current = primitive["function"](current)
            
            return current
        
        return composed


# Example: Build custom pattern detection flow
def create_detection_flow() -> Callable:
    """Create custom control flow for pattern detection."""
    
    builder = ControlFlowBuilder()
    
    # 1. Filter invalid inputs
    builder.add_branch(
        condition=lambda x: x is not None and "text" in x,
        action=lambda x: x
    )
    
    # 2. Extract control flow
    builder.add_transform(
        transform=lambda x: detect_control_flow(x["text"])
    )
    
    # 3. Loop until stable
    builder.add_loop(
        condition=lambda x: x.get("confidence", 0) < 0.9,
        body=lambda x: refine_detection(x),
        max_iterations=10
    )
    
    return builder.build()
```
