"""Minimal read-only Prism Central v4 REST client.

Paths and field names follow the GA v4 namespaces (clustermgmt, vmm,
monitoring). Only GET calls are made, so a Prism Central "viewer" role is
enough.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

DEFAULT_VERSIONS = {"clustermgmt": "v4.0", "vmm": "v4.0", "monitoring": "v4.0"}
MAX_PAGE_SIZE = 100  # v4 list APIs reject $limit above 100


class PrismError(RuntimeError):
    pass


@dataclass
class PrismClient:
    base_url: str
    username: str
    password: str
    verify_tls: bool | str = True
    timeout: float = 30.0
    versions: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_VERSIONS))
    session: requests.Session | None = None

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")
        if self.session is None:
            self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({"Accept": "application/json"})

    def _path(self, namespace: str, resource: str) -> str:
        return f"/api/{namespace}/{self.versions[namespace]}/{resource}"

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = self.session.get(
            f"{self.base_url}{path}", params=params, timeout=self.timeout, verify=self.verify_tls
        )
        if response.status_code >= 400:
            raise PrismError(f"GET {path} failed with HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    def list_all(
        self, path: str, *, page_size: int = MAX_PAGE_SIZE, max_items: int = 10000, filter_expr: str | None = None
    ) -> list[dict]:
        """Follow $page/$limit pagination until the result set is exhausted or max_items is reached."""
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        items: list[dict] = []
        page = 0
        while len(items) < max_items:
            params: dict = {"$page": page, "$limit": page_size}
            if filter_expr:
                params["$filter"] = filter_expr
            payload = self._get(path, params)
            batch = payload.get("data") or []
            items.extend(batch)
            total = (payload.get("metadata") or {}).get("totalAvailableResults")
            if len(batch) < page_size or (isinstance(total, int) and len(items) >= total):
                break
            page += 1
        return items[:max_items]

    def clusters(self) -> list[dict]:
        return self.list_all(self._path("clustermgmt", "config/clusters"))

    def hosts(self) -> list[dict]:
        return self.list_all(self._path("clustermgmt", "config/hosts"))

    def vms(self) -> list[dict]:
        return self.list_all(self._path("vmm", "ahv/config/vms"))

    def unresolved_alerts(self) -> list[dict]:
        return self.list_all(self._path("monitoring", "serviceability/alerts"), filter_expr="isResolved eq false")
