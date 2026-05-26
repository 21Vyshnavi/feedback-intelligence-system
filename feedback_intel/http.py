from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(
    *,
    timeout_s: float = 20.0,
    total_retries: int = 4,
    backoff_factor: float = 0.6,
) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    original = session.request

    def _request(method: str, url: str, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout_s
        return original(method, url, **kwargs)

    session.request = _request  # type: ignore[assignment]
    return session

