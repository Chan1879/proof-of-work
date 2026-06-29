"""Runtime path helpers for local and container execution."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def _can_use_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.touch(exist_ok=True)
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def resolve_runtime_root(
    project_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve a writable runtime root for logs/users/tool data."""
    env = os.environ if env is None else env
    if "PROOF_OF_WORK_DATA_DIR" in env:
        return Path(env["PROOF_OF_WORK_DATA_DIR"]).expanduser()

    if _can_use_directory(Path("/data")):
        return Path("/data")

    root = project_root or Path(__file__).resolve().parent.parent
    return root / ".data"


def resolve_tools_dir(
    project_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the tool directory to load MCP handlers from."""
    env = os.environ if env is None else env
    if "TOOLS_DIR" in env:
        return Path(env["TOOLS_DIR"]).expanduser()

    root = resolve_runtime_root(project_root=project_root, env=env)
    if root == Path("/data"):
        return root / "tools"

    project_root = project_root or Path(__file__).resolve().parent.parent
    return project_root / "tools"


def configure_runtime_environment(
    project_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Populate runtime environment variables with local-safe defaults."""
    env = os.environ if env is None else env
    project_root = project_root or Path(__file__).resolve().parent.parent

    runtime_root = resolve_runtime_root(project_root=project_root, env=env)
    runtime_root.mkdir(parents=True, exist_ok=True)

    defaults = {
        "LOG_DIR": str(runtime_root / "logs"),
        "USERS_DIR": str(runtime_root / "users"),
        "AUDIT_LOG_PATH": str(runtime_root / "logs" / "audit.jsonl"),
        "TOOLS_DIR": str(resolve_tools_dir(project_root=project_root, env=env)),
    }

    for key, value in defaults.items():
        env.setdefault(key, value)

    return defaults
