"""Structured audit logger for MCP resume policy decisions.

Writes JSON-lines to a configurable log path so every policy evaluation,
tool invocation, and verification event is traceable.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path(os.environ.get("AUDIT_LOG_PATH", "/data/logs/audit.jsonl"))

logger = logging.getLogger("resume_audit")
logger.setLevel(logging.INFO)


def _ts() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def log_event(
    event_type: str,
    tool_name: str | None = None,
    payload: dict[str, Any] | None = None,
    decision: dict[str, Any] | None = None,
    user_slug: str = "default",
) -> None:
    """Append a structured JSON record to the audit log.

    Args:
        event_type: Category of the event (e.g. ``"policy_eval"``,
            ``"tool_call"``, ``"contract_output_error"``).
        tool_name: MCP tool that triggered the event, or ``None``.
        payload: Tool input payload (only keys are logged, not values).
        decision: Policy decision dict (``blocked``, ``reasons``, etc.).
        user_slug: Filesystem-safe user identifier.

    The record is written as a single JSON line to ``AUDIT_LOG_PATH``.
    For ``finalize_resume`` events the SHA-256 fingerprint of the resume
    draft is captured for compliance auditing.
    """
    record: dict[str, Any] = {
        "ts": _ts(),
        "event": event_type,
        "tool": tool_name,
        "user": user_slug,
        "payload_keys": sorted(payload.keys()) if payload else [],
        "decision": decision,
    }

    # For finalize events, capture a content fingerprint so the exact
    # resume output can be audited later without bloating every log line.
    if payload and tool_name == "finalize_resume":
        resume_text = payload.get("resume_draft", "")
        if resume_text:
            record["resume_sha256"] = hashlib.sha256(
                resume_text.encode("utf-8")
            ).hexdigest()
            record["resume_length"] = len(resume_text)

    line = json.dumps(record, default=str)
    logger.info(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass  # non-blocking; container may lack write access on first run
