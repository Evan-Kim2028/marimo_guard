from __future__ import annotations

from pathlib import Path

from marimo_guard.service_layer.session_service import NotebookSessionService


class MockMarimoClient:
    def __init__(self, notebooks=None):
        self.notebooks = notebooks or []

    def get_active_notebooks(self):
        return self.notebooks


def test_get_active_sessions():
    client = MockMarimoClient([
        {"session_id": "abc123", "file_path": "/path/to/notebook.py", "status": "active"},
        {"session_id": "def456", "file_path": "/other/notebook.py", "status": "active"},
    ])
    service = NotebookSessionService(client)  # type: ignore[arg-type]
    sessions = service.get_active_sessions()
    assert len(sessions) == 2
    assert sessions[0].session_id == "abc123"
    assert sessions[0].file_path == Path("/path/to/notebook.py")
    assert sessions[1].session_id == "def456"


def test_is_notebook_active():
    client = MockMarimoClient([
        {"session_id": "abc123", "file_path": "/path/to/notebook.py"},
    ])
    service = NotebookSessionService(client)  # type: ignore[arg-type]
    assert service.is_notebook_active(Path("/path/to/notebook.py")) is True
    # Different filename should not match
    assert service.is_notebook_active(Path("/other/another.py")) is False


def test_is_notebook_active_by_name():
    client = MockMarimoClient([
        {"session_id": "abc123", "file_path": "/some/path/notebook.py"},
    ])
    service = NotebookSessionService(client)  # type: ignore[arg-type]
    assert service.is_notebook_active(Path("/different/path/notebook.py")) is True


def test_get_session_for_notebook():
    client = MockMarimoClient([
        {"session_id": "abc123", "file_path": "/path/to/notebook.py"},
    ])
    service = NotebookSessionService(client)  # type: ignore[arg-type]
    session = service.get_session_for_notebook(Path("/path/to/notebook.py"))
    assert session is not None
    assert session.session_id == "abc123"
    no_session = service.get_session_for_notebook(Path("/other/another.py"))
    assert no_session is None
