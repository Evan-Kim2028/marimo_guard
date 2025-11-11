"""HTTP client for connecting to marimo's MCP server endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from ..http_client import HttpClient

logger = logging.getLogger(__name__)


class MarimoMCPClient:
    """Client for connecting to marimo's MCP server endpoint.
    
    Connects to marimo's HTTP MCP server at http://localhost:PORT/mcp/server
    to query active notebooks and error summaries.
    """

    def __init__(
        self,
        base_url: str,
        http_client: HttpClient,
        *,
        connection_timeout: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client
        self.connection_timeout = connection_timeout

    def get_active_notebooks(self) -> list[dict[str, Any]]:
        try:
            response = self.http_client.request(
                "POST",
                f"{self.base_url}/prompts/active_notebooks",
                json={},
                timeout=self.connection_timeout,
                ok_statuses=(200,),
            )
            data = response.json()
            return self._parse_mcp_response(data, default=[])
        except requests.RequestException as e:
            logger.debug("Failed to get active notebooks from marimo: %s", e)
            raise

    def get_errors_summary(self) -> dict[str, Any]:
        try:
            response = self.http_client.request(
                "POST",
                f"{self.base_url}/prompts/errors_summary",
                json={},
                timeout=self.connection_timeout,
                ok_statuses=(200,),
            )
            data = response.json()
            default_summary = {"notebooks": {}, "total_errors": 0}
            parsed = self._parse_mcp_response(data, default=default_summary)
            if isinstance(parsed, dict):
                return parsed
            return default_summary
        except requests.RequestException as e:
            logger.debug("Failed to get errors summary from marimo: %s", e)
            raise

    def health_check(self) -> bool:
        try:
            response = self.http_client.request(
                "GET",
                f"{self.base_url.replace('/mcp/server', '')}/health",
                timeout=self.connection_timeout,
                ok_statuses=(200, 404, 405),
            )
            return True
        except requests.RequestException:
            try:
                response = self.http_client.request(
                    "POST",
                    f"{self.base_url}/prompts/active_notebooks",
                    json={},
                    timeout=self.connection_timeout,
                    ok_statuses=(200, 400, 404),
                )
                return True
            except requests.RequestException:
                return False

    def _parse_mcp_response(self, data: dict[str, Any] | list, *, default: Any) -> Any:
        if isinstance(data, dict):
            if "content" in data:
                content = data["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                    try:
                        parsed = json.loads(text_content)
                        return parsed
                    except (json.JSONDecodeError, AttributeError):
                        pass
            return data
        elif isinstance(data, list):
            return data
        logger.warning("Unexpected response format from marimo MCP server: %s", data)
        return default

