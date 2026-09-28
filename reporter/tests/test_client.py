import pytest

from ntnx_report.client import PrismClient, PrismError


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, pages, status=200):
        self.pages = pages
        self.status = status
        self.calls = []
        self.headers = {}
        self.auth = None

    def get(self, url, params=None, timeout=None, verify=None):
        self.calls.append((url, dict(params or {}), verify))
        page = params["$page"]
        return FakeResponse(self.status, self.pages[page] if page < len(self.pages) else {"data": []})


def client(session, **kwargs):
    return PrismClient("https://pc:9440/", "viewer", "secret", session=session, **kwargs)


def test_paginates_until_total_reached():
    pages = [
        {"data": [{"extId": str(i)} for i in range(100)], "metadata": {"totalAvailableResults": 150}},
        {"data": [{"extId": str(i)} for i in range(100, 150)], "metadata": {"totalAvailableResults": 150}},
    ]
    session = FakeSession(pages)
    vms = client(session).vms()
    assert len(vms) == 150
    assert [c[1]["$page"] for c in session.calls] == [0, 1]
    assert session.calls[0][0] == "https://pc:9440/api/vmm/v4.0/ahv/config/vms"
    assert session.calls[0][1]["$limit"] == 100


def test_uses_ga_v4_paths_and_alert_filter():
    session = FakeSession([{"data": []}])
    c = client(session, versions={"clustermgmt": "v4.1", "vmm": "v4.1", "monitoring": "v4.1"})
    c.clusters()
    c.hosts()
    c.unresolved_alerts()
    urls = [call[0] for call in session.calls]
    assert urls == [
        "https://pc:9440/api/clustermgmt/v4.1/config/clusters",
        "https://pc:9440/api/clustermgmt/v4.1/config/hosts",
        "https://pc:9440/api/monitoring/v4.1/serviceability/alerts",
    ]
    assert session.calls[2][1]["$filter"] == "isResolved eq false"


def test_page_size_is_capped_and_max_items_respected():
    session = FakeSession([{"data": [{"extId": str(i)} for i in range(100)]}] * 5)
    items = client(session).list_all("/api/vmm/v4.0/ahv/config/vms", page_size=500, max_items=250)
    assert len(items) == 250
    assert all(call[1]["$limit"] == 100 for call in session.calls)


def test_http_errors_raise():
    with pytest.raises(PrismError, match="HTTP 401"):
        client(FakeSession([{}], status=401)).clusters()
