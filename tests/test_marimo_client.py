from __future__ import annotations

from marimo_guard.adapters.marimo.client import MarimoMCPClient


class StubResponse:
    def __init__(self, data, *, status: int = 200, headers: dict | None = None):
        self._data = data
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class StubHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("No stubbed responses remaining")
        return self.responses.pop(0)


def test_get_active_notebooks_success():
    http_client = StubHttpClient([
        StubResponse({
            "content": [
                {
                    "text": '[{"session_id": "abc123", "file_path": "/path/to/notebook.py", "status": "active"}]'
                }
            ]
        })
    ])
    client = MarimoMCPClient(base_url="http://localhost:2718/mcp/server", http_client=http_client)  # type: ignore[arg-type]
    notebooks = client.get_active_notebooks()
    assert len(notebooks) == 1
    assert notebooks[0]["session_id"] == "abc123"
    assert notebooks[0]["file_path"] == "/path/to/notebook.py"


def test_get_errors_summary_direct_format():
    http_client = StubHttpClient([
        StubResponse({
            "notebooks": {"/path/to/notebook.py": ["Error 1"]},
            "total_errors": 1,
        })
    ])
    client = MarimoMCPClient(base_url="http://localhost:2718/mcp/server", http_client=http_client)  # type: ignore[arg-type]
    summary = client.get_errors_summary()
    assert summary["total_errors"] == 1
    assert "/path/to/notebook.py" in summary["notebooks"]

