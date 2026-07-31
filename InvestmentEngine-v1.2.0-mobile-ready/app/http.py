from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(
    user_agent: str = "RosaInvestmentEngine/1.1.4",
    *,
    total_retries: int = 4,
    connect_retries: int | None = None,
    read_retries: int | None = None,
    backoff_factor: float = 0.6,
) -> requests.Session:
    connect = total_retries if connect_retries is None else connect_retries
    read = total_retries if read_retries is None else read_retries
    retry = Retry(
        total=total_retries,
        connect=connect,
        read=read,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
    session.mount("https://", adapter)
    return session
