"""Tiny in-memory Prism Central v4 stand-in for playbook tests.

Implements only the endpoints the playbooks call and enforces the same
contract a real Prism Central does for mutations: basic auth, an If-Match
header equal to the entity's current ETag, and an NTNX-Request-Id header.
"""

from __future__ import annotations

import base64
import json
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

USER, PASSWORD = "admin", "nutanix/4u"
POWER = {"power-on": "ON", "power-off": "OFF", "guest-shutdown": "OFF", "shutdown": "OFF"}


class State:
    def __init__(self):
        self.vms = {
            str(uuid.uuid4()): {"name": n, "powerState": p, "numSockets": s, "numCoresPerSocket": 2,
                                "memorySizeBytes": m * 1024**3, "cluster": {"extId": "cluster-1"}, "categories": []}
            for n, p, s, m in [("lab-web-01", "OFF", 1, 4), ("lab-db-01", "ON", 2, 16), ("lab-app-01", "ON", 1, 8)]
        }
        for ext_id, vm in self.vms.items():
            vm["extId"] = ext_id
        self.etags = {ext_id: 1 for ext_id in self.vms}
        self.categories = [
            {"extId": str(uuid.uuid4()), "key": "DR-Tier", "value": "PP-NEARSYNC-15M"},
            {"extId": str(uuid.uuid4()), "key": "Environment", "value": "Lab"},
        ]
        self.mutations: list[dict] = []
        self.lock = threading.Lock()

    def etag(self, ext_id):
        return f'W/"{self.etags[ext_id]}"'


def _filter_eq(expr: str, field: str) -> str | None:
    match = re.search(rf"{field} eq '([^']*)'", expr or "")
    return match.group(1) if match else None


class Handler(BaseHTTPRequestHandler):
    state: State

    def log_message(self, *args):
        pass

    def _send(self, code, payload=None, headers=None):
        body = json.dumps(payload or {}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        expected = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        if self.headers.get("Authorization") != expected:
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self._authorized():
            return
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        s = self.state
        if url.path == "/api/vmm/v4.0/ahv/config/vms":
            vms = sorted(s.vms.values(), key=lambda v: v["name"])
            name = _filter_eq(q.get("$filter", ""), "name")
            if name is not None:
                vms = [v for v in vms if v["name"] == name]
            page, limit = int(q.get("$page", 0)), int(q.get("$limit", 50))
            if limit > 100:
                return self._send(400, {"error": "$limit must be <= 100"})
            chunk = vms[page * limit:(page + 1) * limit]
            return self._send(200, {"data": chunk, "metadata": {"totalAvailableResults": len(vms)}})
        m = re.fullmatch(r"/api/vmm/v4\.0/ahv/config/vms/([^/]+)", url.path)
        if m and m.group(1) in s.vms:
            return self._send(200, {"data": s.vms[m.group(1)]}, {"ETag": s.etag(m.group(1))})
        if re.fullmatch(r"/api/prism/v4\.0/config/tasks/[^/]+", url.path):
            return self._send(200, {"data": {"extId": url.path.rsplit("/", 1)[1], "status": "SUCCEEDED"}})
        if url.path == "/api/prism/v4.0/config/categories":
            key, value = _filter_eq(q.get("$filter", ""), "key"), _filter_eq(q.get("$filter", ""), "value")
            data = [c for c in s.categories if c["key"] == key and c["value"] == value]
            return self._send(200, {"data": data} if data else {"metadata": {"totalAvailableResults": 0}})
        self._send(404, {"error": f"no route {url.path}"})

    def do_POST(self):
        if not self._authorized():
            return
        s = self.state
        m = re.fullmatch(r"/api/vmm/v4\.0/ahv/config/vms/([^/]+)/\$actions/([a-z-]+)", urlparse(self.path).path)
        if not m or m.group(1) not in s.vms:
            return self._send(404, {"error": "not found"})
        ext_id, action = m.groups()
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        with s.lock:
            if not self.headers.get("NTNX-Request-Id"):
                return self._send(400, {"error": "NTNX-Request-Id header is required"})
            if self.headers.get("If-Match") != s.etag(ext_id):
                return self._send(412, {"error": "ETag mismatch"})
            vm = s.vms[ext_id]
            if action in POWER:
                vm["powerState"] = POWER[action]
            elif action == "associate-categories":
                known = {c["extId"] for c in s.categories}
                refs = body.get("categories") or []
                if not refs or any(r.get("extId") not in known for r in refs):
                    return self._send(400, {"error": "invalid categories"})
                vm["categories"] = [{"extId": r["extId"]} for r in refs]
            else:
                return self._send(404, {"error": f"unknown action {action}"})
            s.etags[ext_id] += 1
            s.mutations.append({"vm": vm["name"], "action": action, "request_id": self.headers["NTNX-Request-Id"]})
        self._send(202, {"data": {"extId": f"task-{uuid.uuid4()}"}})


def start(port: int = 0):
    state = State()
    handler = type("BoundHandler", (Handler,), {"state": state})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state
