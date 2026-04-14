"""Proof of Work — dynamic tool loader.

On startup the server scans ``TOOLS_DIR`` (default ``/data/tools/``) for
Python files that export a ``TOOL_DEF`` dict and registers each one with
FastMCP.  If the tools directory is empty the baked-in defaults under
``/app/tools/`` are used instead (the entrypoint.sh bootstrap copies them
on first run).

Architecture
------------
Tools are thin handler wrappers.  The heavy lifting lives in two packages:

- **engine/** — Policy evaluation, contract validation, session state, audit
  logging.  Every tool response passes through ``engine.session.finalize_tool_response``.
- **helpers/** — Naming/path utilities, interactive question generation, and
  per-user data persistence (skills, preferences, history).
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that ``engine.*`` and
# ``helpers.*`` imports resolve regardless of how the process is launched.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Logging configuration — writes to /data/logs/server.log
# ---------------------------------------------------------------------------
LOG_DIR = Path(os.environ.get("LOG_DIR", "/data/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)

_file_handler = RotatingFileHandler(
    LOG_DIR / "server.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
_root_logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
_root_logger.addHandler(_console_handler)

logger = logging.getLogger("mcp_server")


def _resolve_port() -> int:
    """Resolve server port from env with a safe default.

    Priority:
    1) MCP_PORT
    2) PORT (fallback for platform conventions)
    3) 5359
    """
    raw = os.environ.get("MCP_PORT", os.environ.get("PORT", "5359"))
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid port value '%s'; falling back to 5359", raw)
        return 5359

# ---------------------------------------------------------------------------
# Tool loading
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(os.environ.get("TOOLS_DIR", "/data/tools"))


def _load_tool_module(filepath: Path):
    """Import a single tool .py file and return its TOOL_DEF dict."""
    spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {filepath}")
    mod = importlib.util.module_from_spec(spec)
    # Ensure the parent dir is on sys.path so relative imports inside tools
    # can find session, naming, etc.
    parent = str(filepath.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec.loader.exec_module(mod)
    tool_def = getattr(mod, "TOOL_DEF", None)
    if tool_def is None:
        raise AttributeError(f"{filepath} does not export TOOL_DEF")
    return tool_def


def load_tools(mcp_app: FastMCP, directory: Path) -> int:
    """Scan *directory* for ``*.py`` files, load each, and register tools.

    Returns the number of tools successfully loaded.
    """
    count = 0
    if not directory.is_dir():
        logger.warning("Tools directory %s does not exist — no tools loaded", directory)
        return count

    for py_file in sorted(directory.glob("*.py")):
        try:
            tool_def = _load_tool_module(py_file)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load tool from %s", py_file)
            continue

        handler = tool_def["handler"]
        name = tool_def.get("name", handler.__name__)
        description = tool_def.get("description", handler.__doc__ or "")

        # Register with FastMCP — the decorator approach is replaced by
        # the programmatic ``mcp_app.tool()`` wrapper.
        mcp_app.tool(name=name, description=description)(handler)
        logger.info("Loaded tool '%s' from %s", name, py_file.name)
        count += 1

    return count


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
mcp = FastMCP("proof-of-work")

loaded = load_tools(mcp, TOOLS_DIR)
if loaded == 0:
    # Fallback: try baked-in tools packaged with the image
    fallback = Path("/app/tools")
    if fallback.is_dir():
        logger.info("No tools in %s — falling back to %s", TOOLS_DIR, fallback)
        loaded = load_tools(mcp, fallback)

if loaded == 0:
    msg = (
        "No MCP tools were registered. In container mode ensure /data/tools "
        "is populated or /app/tools is present."
    )
    logger.error(msg)
    raise RuntimeError(msg)

logger.info("Server ready — %d tool(s) registered", loaded)


if __name__ == "__main__":
    # transport="http" uses Streamable HTTP (replaces legacy SSE)
    # host="0.0.0.0" is required for Docker access
    mcp.run(transport="http", host="0.0.0.0", port=_resolve_port())
