"""HTTP client utilities for simple retries and timeouts."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass

import requests

logger = logging.getLogger("marimo_guard.http")


@dataclass(frozen=True)
class HttpClientConfig:
    timeout_seconds: float = 15.0
    max_retries: int = 3
    backoff_initial: float = 0.35
    backoff_max: float = 5.0
    jitter_range: tuple[float, float] = (1.25, 2.25)
    retry_statuses: tuple[int, ...] = (408, 409, 425, 429, 500, 502, 503, 504)


class HttpClient:
    def __init__(self, config: HttpClientConfig, *, session: requests.Session | None = None) -> None:
        self._config = config
        self._session = session or requests.Session()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, object] | None = None,
        json: object | None = None,
        data: object | None = None,
        timeout: float | None = None,
        ok_statuses: Iterable[int] | None = None,
    ) -> requests.Response:
        attempt = 0
        backoff = self._config.backoff_initial
        timeout_value = timeout or self._config.timeout_seconds

        while True:
            start = time.perf_counter()
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=_clone_mapping(headers),
                    params=params,
                    json=json,
                    data=data,
                    timeout=timeout_value,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "http_request_error",
                    extra={"method": method, "url": url, "attempt": attempt, "error": str(exc)},
                )
                if attempt >= self._config.max_retries:
                    raise
                _sleep(backoff, self._config)
                backoff = min(self._config.backoff_max, backoff * 2)
                attempt += 1
                continue

            duration_ms = int((time.perf_counter() - start) * 1000)
            status = response.status_code
            logger.debug(
                "http_request",
                extra={"method": method, "url": url, "status": status, "attempt": attempt, "duration_ms": duration_ms},
            )

            if _should_retry(status, attempt, self._config):
                _sleep(backoff, self._config)
                backoff = min(self._config.backoff_max, backoff * 2)
                attempt += 1
                continue

            if ok_statuses and status in ok_statuses:
                return response

            response.raise_for_status()
            return response


def _should_retry(status: int, attempt: int, config: HttpClientConfig) -> bool:
    return status in config.retry_statuses and attempt < config.max_retries


def _sleep(backoff: float, config: HttpClientConfig) -> None:
    jitter = random.uniform(*config.jitter_range)
    time.sleep(backoff * jitter)


def _clone_mapping(mapping: Mapping[str, str] | None) -> MutableMapping[str, str] | None:
    if mapping is None:
        return None
    return dict(mapping)

