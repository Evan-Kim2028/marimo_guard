"""Service for managing marimo notebook sessions (standalone)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marimo_guard.adapters.marimo.client import MarimoMCPClient

logger = logging.getLogger(__name__)


@dataclass
class NotebookSession:
    """Represents an active marimo notebook session."""

    session_id: str
    file_path: Path
    status: str = "active"
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)


class NotebookSessionService:
    """Service for tracking active marimo notebook sessions via MCP client."""

    def __init__(self, marimo_client: MarimoMCPClient):
        self.marimo_client = marimo_client

    def get_active_sessions(self) -> list[NotebookSession]:
        try:
            notebooks = self.marimo_client.get_active_notebooks()
            sessions: list[NotebookSession] = []
            for nb in notebooks:
                if isinstance(nb, dict):
                    session_id = nb.get("session_id") or nb.get("id") or str(nb.get("file_path", ""))
                    file_path = nb.get("file_path") or nb.get("path")
                    if not file_path:
                        continue
                    sessions.append(
                        NotebookSession(
                            session_id=str(session_id),
                            file_path=Path(file_path),
                            status=nb.get("status", "active"),
                            metadata=nb,
                        )
                    )
            return sessions
        except Exception as e:
            logger.debug("Failed to get active sessions from marimo: %s", e)
            return []

    def is_notebook_active(self, notebook_path: Path) -> bool:
        try:
            sessions = self.get_active_sessions()
            notebook_path = notebook_path.expanduser().resolve()
            for session in sessions:
                session_path = session.file_path.expanduser().resolve()
                if session_path == notebook_path or session_path.name == notebook_path.name:
                    return True
            return False
        except Exception as e:
            logger.debug("Failed to check if notebook is active: %s", e)
            return False

    def get_session_for_notebook(self, notebook_path: Path) -> NotebookSession | None:
        try:
            sessions = self.get_active_sessions()
            notebook_path = notebook_path.expanduser().resolve()
            for session in sessions:
                session_path = session.file_path.expanduser().resolve()
                if session_path == notebook_path or session_path.name == notebook_path.name:
                    return session
            return None
        except Exception as e:
            logger.debug("Failed to get session for notebook: %s", e)
            return None

    def warn_if_active(self, notebook_path: Path) -> str | None:
        session = self.get_session_for_notebook(notebook_path)
        if session:
            return (
                f"Notebook is currently open in marimo (session: {session.session_id}). "
                "Refreshing data may cause conflicts with active editing session."
            )
        return None

