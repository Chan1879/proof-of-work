"""Engine package — core policy, contract, session, and audit infrastructure.

This package contains the server-side enforcement layer that every MCP tool
call passes through: input/output contract validation, policy rule evaluation,
per-user session state management, and structured audit logging.

Quick imports::

    from engine import PolicyEngine, ContractRegistry, log_event
    from engine.session import get_session, policy_check
"""
from engine.audit import log_event
from engine.contracts import ContractRegistry, ContractValidationError
from engine.policy_engine import PolicyDecision, PolicyEngine
from engine.session import (
    finalize_tool_response,
    get_session,
    policy_check,
    set_current_user,
)

__all__ = [
    "ContractRegistry",
    "ContractValidationError",
    "PolicyDecision",
    "PolicyEngine",
    "finalize_tool_response",
    "get_session",
    "log_event",
    "policy_check",
    "set_current_user",
]
