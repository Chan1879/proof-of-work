"""Per-user persistent data store for the MCP resume server.

Manages user identity, skill storage, preferences, and session history.
All data is isolated per user under ``USERS_DIR/<slug>/``.  Anonymous
(default) users have no on-disk footprint.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("user_store")

USERS_DIR = Path(os.environ.get("USERS_DIR", "/data/users"))

_MAX_SLUG_LEN = 64
_SLUG_RE = re.compile(r"[^a-z0-9]+")

_file_lock = threading.Lock()


# ---------------------------------------------------------------------------
# UserContext — immutable identity bag returned to callers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UserContext:
    """Immutable identity bag returned to callers.

    Attributes:
        slug: Filesystem-safe user identifier.
        display_name: Human-readable name.
        is_anonymous: ``True`` for the default/anonymous user.
        data_dir: Absolute path to the user's data directory, or
            ``None`` for anonymous users.
    """

    slug: str
    display_name: str
    is_anonymous: bool
    data_dir: Optional[Path] = field(default=None, repr=False)


_ANONYMOUS = UserContext(
    slug="default",
    display_name="Anonymous",
    is_anonymous=True,
    data_dir=None,
)


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------
def _slugify(name: str) -> str:
    """Convert a display name to a filesystem-safe slug.

    Args:
        name: Raw display name.

    Returns:
        Lower-case, hyphen-separated slug (max 64 chars), or
        ``"default"`` if the name is empty/whitespace.
    """
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug[:_MAX_SLUG_LEN] if slug else "default"


# ---------------------------------------------------------------------------
# Safe JSON file helpers (thread-safe, non-blocking on OS errors)
# ---------------------------------------------------------------------------
def _read_json(path: Path, default: Any = None) -> Any:
    """Thread-safe JSON read that returns *default* on any error."""
    try:
        with _file_lock:
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    """Atomically write *data* as JSON via a temp-file rename."""
    try:
        with _file_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            tmp.replace(path)
    except OSError:
        logger.warning("Failed to write %s", path, exc_info=True)


# ---------------------------------------------------------------------------
# UserStore — stateless helper class (all state lives on disk)
# ---------------------------------------------------------------------------
class UserStore:
    """Manage per-user data directories under *USERS_DIR*.

    All state lives on disk; this class is stateless and thread-safe.
    Each user gets their own directory containing ``skills.json``,
    ``preferences.json``, and ``history.json``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or USERS_DIR

    # -- identity -----------------------------------------------------------

    def identify(self, name: str) -> UserContext:
        """Resolve a display name to a :class:`UserContext`.

        Creates the user's data directory on first identification.

        Args:
            name: Human-readable display name.

        Returns:
            A :class:`UserContext` for the identified (or anonymous) user.
        """
        slug = _slugify(name)
        if slug == "default":
            return _ANONYMOUS
        data_dir = self.root / slug
        data_dir.mkdir(parents=True, exist_ok=True)
        return UserContext(
            slug=slug,
            display_name=name.strip(),
            is_anonymous=False,
            data_dir=data_dir,
        )

    @staticmethod
    def get_anonymous() -> UserContext:
        return _ANONYMOUS

    def user_exists(self, slug: str) -> bool:
        return (self.root / slug).is_dir()

    # -- skills -------------------------------------------------------------

    def _skills_path(self, ctx: UserContext) -> Path | None:
        if ctx.is_anonymous or ctx.data_dir is None:
            return None
        return ctx.data_dir / "skills.json"

    def get_skills(self, ctx: UserContext) -> list[dict[str, Any]]:
        path = self._skills_path(ctx)
        if path is None:
            return []
        raw = _read_json(path, default=[])
        return [s for s in raw if isinstance(s, dict) and s.get("name")]

    def add_skills(self, ctx: UserContext, skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Append *skills* to the user's skill store.

        Args:
            ctx: Target user context.
            skills: Skill dicts to persist (``added_at`` auto-set).

        Returns:
            The full skill list after appending.
        """
        if ctx.is_anonymous:
            return []
        path = self._skills_path(ctx)
        if path is None:
            return []
        existing = _read_json(path, default=[])
        ts = datetime.now(timezone.utc).isoformat()
        for skill in skills:
            skill.setdefault("added_at", ts)
        existing.extend(skills)
        _write_json(path, existing)
        return existing

    def remove_skills(self, ctx: UserContext, skill_names: list[str]) -> list[dict[str, Any]]:
        """Remove skills by name (case-insensitive).

        Args:
            ctx: Target user context.
            skill_names: Names to remove.

        Returns:
            Remaining skill list after deletion.
        """
        if ctx.is_anonymous:
            return []
        path = self._skills_path(ctx)
        if path is None:
            return []
        existing = _read_json(path, default=[])
        lower_names = {n.lower() for n in skill_names}
        remaining = [
            s for s in existing
            if isinstance(s, dict) and s.get("name", "").lower() not in lower_names
        ]
        _write_json(path, remaining)
        return remaining

    # -- preferences --------------------------------------------------------

    def _prefs_path(self, ctx: UserContext) -> Path | None:
        if ctx.is_anonymous or ctx.data_dir is None:
            return None
        return ctx.data_dir / "preferences.json"

    def get_preferences(self, ctx: UserContext) -> dict[str, Any]:
        path = self._prefs_path(ctx)
        if path is None:
            return {}
        return _read_json(path, default={})

    def save_preferences(self, ctx: UserContext, prefs: dict[str, Any]) -> None:
        if ctx.is_anonymous:
            return
        path = self._prefs_path(ctx)
        if path is None:
            return
        existing = _read_json(path, default={})
        existing.update(prefs)
        _write_json(path, existing)

    # -- session history ----------------------------------------------------

    def _history_path(self, ctx: UserContext) -> Path | None:
        if ctx.is_anonymous or ctx.data_dir is None:
            return None
        return ctx.data_dir / "history.json"

    def get_session_history(self, ctx: UserContext, limit: int = 10) -> list[dict[str, Any]]:
        path = self._history_path(ctx)
        if path is None:
            return []
        history = _read_json(path, default=[])
        return history[-limit:]

    def append_session_history(self, ctx: UserContext, entry: dict[str, Any]) -> None:
        if ctx.is_anonymous:
            return
        path = self._history_path(ctx)
        if path is None:
            return
        history = _read_json(path, default=[])
        entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
        history.append(entry)
        _write_json(path, history)
