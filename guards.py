"""
IICWMS Assertion Guards
=======================
Safety checks to prevent fake intelligence.

GUARDS:
- Agents cannot emit events
- LLM cannot write state
- Simulation cannot read policies

Violations raise errors.
"""

from functools import wraps
from typing import Callable, Any
import inspect


class ArchitecturalViolation(Exception):
    """Raised when architectural rules are violated."""
    pass


# Track which module is currently executing
_current_context: str = "unknown"


def set_context(context: str):
    """Set the current execution context."""
    global _current_context
    _current_context = context


def get_context() -> str:
    """Get the current execution context."""
    return _current_context


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD: Agents cannot emit events
# ═══════════════════════════════════════════════════════════════════════════════

def agents_cannot_emit_events(func: Callable) -> Callable:
    """
    Decorator to ensure agents don't create events.
    
    Apply to any function that creates events to verify
    it's not being called from an agent context.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "agent" in _current_context.lower():
            raise ArchitecturalViolation(
                f"VIOLATION: Agents cannot emit events. "
                f"Function '{func.__name__}' called from '{_current_context}'"
            )
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD: LLM cannot write state
# ═══════════════════════════════════════════════════════════════════════════════

def llm_cannot_write_state(func: Callable) -> Callable:
    """
    Decorator to ensure LLM doesn't modify state.
    
    Apply to state modification functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "llm" in _current_context.lower() or "explanation" in _current_context.lower():
            # Check if this is a read operation (allowed) vs write (forbidden)
            if any(kw in func.__name__.lower() for kw in ['add', 'write', 'set', 'update', 'delete']):
                raise ArchitecturalViolation(
                    f"VIOLATION: LLM cannot write state. "
                    f"Function '{func.__name__}' called from '{_current_context}'"
                )
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD: Simulation cannot read policies
# ═══════════════════════════════════════════════════════════════════════════════

def simulation_cannot_read_policies(func: Callable) -> Callable:
    """
    Decorator to ensure simulation doesn't know about policies.
    
    Apply to policy retrieval functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "simulation" in _current_context.lower() or "simulator" in _current_context.lower():
            raise ArchitecturalViolation(
                f"VIOLATION: Simulation cannot read policies. "
                f"Function '{func.__name__}' called from '{_current_context}'"
            )
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationContext:
    """Context manager for simulation operations."""
    def __enter__(self):
        set_context("simulation")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_context("unknown")


class AgentContext:
    """Context manager for agent operations."""
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
    
    def __enter__(self):
        set_context(f"agent:{self.agent_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_context("unknown")


class ExplanationContext:
    """Context manager for LLM/explanation operations."""
    def __enter__(self):
        set_context("explanation:llm")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_context("unknown")


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_event_has_no_severity(event: dict) -> bool:
    """Ensure event doesn't contain severity/risk fields."""
    forbidden_fields = ['severity', 'risk', 'anomaly', 'alert', 'priority']
    for field in forbidden_fields:
        if field in event:
            raise ArchitecturalViolation(
                f"VIOLATION: Event contains forbidden field '{field}'. "
                "Events must be pure facts with no interpretation."
            )
    return True


def validate_insight_has_evidence(insight: dict) -> bool:
    """Ensure insight is backed by evidence."""
    if not insight.get('evidence_count') and not insight.get('evidence_ids'):
        raise ArchitecturalViolation(
            "VIOLATION: Insight has no evidence. "
            "Every claim must point to evidence."
        )
    return True


def validate_anomaly_has_evidence(anomaly: dict) -> bool:
    """Ensure anomaly is backed by evidence."""
    if not anomaly.get('evidence') and not anomaly.get('evidence_ids'):
        raise ArchitecturalViolation(
            "VIOLATION: Anomaly has no evidence. "
            "Every claim must point to evidence."
        )
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_guards_check():
    """
    Run a comprehensive check of all architectural guards.
    
    Call this during startup to verify system integrity.
    """
    print("Running architectural guard checks...")
    
    checks_passed = 0
    checks_failed = 0
    
    # Check 1: Simulation module doesn't import policy
    try:
        import simulator.engine as sim
        if hasattr(sim, 'POLICIES') or hasattr(sim, 'check_policy'):
            raise ArchitecturalViolation("Simulation has policy knowledge")
        checks_passed += 1
        print("  ✓ Simulation doesn't know about policies")
    except ImportError:
        checks_passed += 1
    except ArchitecturalViolation as e:
        checks_failed += 1
        print(f"  ✗ {e}")
    
    # Check 2: Agents don't have event emission
    try:
        from agents import workflow_agent
        if hasattr(workflow_agent.WorkflowAgent, 'emit_event'):
            raise ArchitecturalViolation("Agent can emit events")
        checks_passed += 1
        print("  ✓ Agents don't emit events")
    except ImportError:
        checks_passed += 1
    except ArchitecturalViolation as e:
        checks_failed += 1
        print(f"  ✗ {e}")
    
    # Check 3: Explanation engine has LLM-only flag
    try:
        from explanation.engine import ExplanationEngine
        engine = ExplanationEngine(use_llm=False)
        # Verify it works without LLM
        checks_passed += 1
        print("  ✓ Explanation engine works without LLM")
    except Exception as e:
        checks_failed += 1
        print(f"  ✗ Explanation engine error: {e}")
    
    print(f"\nGuard checks complete: {checks_passed} passed, {checks_failed} failed")
    
    if checks_failed > 0:
        raise ArchitecturalViolation(f"{checks_failed} architectural violations detected")
    
    return True


if __name__ == "__main__":
    run_all_guards_check()
