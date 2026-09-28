"""Run the real playbooks against the mock Prism Central v4 API."""

import csv
import json
import os
import subprocess
from pathlib import Path

import pytest

from mock_prism import PASSWORD, USER, start

ANSIBLE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def prism():
    server, state = start()
    yield server, state
    server.shutdown()


def run_playbook(server, playbook, extra):
    env = dict(os.environ, NUTANIX_USERNAME=USER, NUTANIX_PASSWORD=PASSWORD, ANSIBLE_CONFIG=str(ANSIBLE_DIR / "ansible.cfg"))
    extra = {"prism_scheme": "http", "prism_host": "127.0.0.1", "prism_port": server.server_address[1],
             "task_poll_delay": 0, **extra}
    return subprocess.run(
        ["ansible-playbook", "-i", str(ANSIBLE_DIR / "inventory.yml"), str(ANSIBLE_DIR / "playbooks" / playbook),
         "-e", json.dumps(extra)],
        cwd=ANSIBLE_DIR, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False,
    )


def vm(state, name):
    return next(v for v in state.vms.values() if v["name"] == name)


def test_power_on_uses_etag_and_request_id_and_is_idempotent(prism):
    server, state = prism
    result = run_playbook(server, "vm_power.yml", {"vm_names": ["lab-web-01"], "power_action": "power-on"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert vm(state, "lab-web-01")["powerState"] == "ON"
    assert [m["action"] for m in state.mutations] == ["power-on"]
    assert state.mutations[0]["request_id"]

    again = run_playbook(server, "vm_power.yml", {"vm_names": ["lab-web-01"], "power_action": "power-on"})
    assert again.returncode == 0
    assert len(state.mutations) == 1, "second run must not send another power-on"


def test_guest_shutdown_multiple_vms(prism):
    server, state = prism
    result = run_playbook(server, "vm_power.yml", {"vm_names": ["lab-db-01", "lab-app-01"], "power_action": "guest-shutdown"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert vm(state, "lab-db-01")["powerState"] == vm(state, "lab-app-01")["powerState"] == "OFF"


def test_unknown_vm_fails(prism):
    server, state = prism
    result = run_playbook(server, "vm_power.yml", {"vm_names": ["does-not-exist"], "power_action": "power-on"})
    assert result.returncode != 0
    assert "Expected exactly one VM named 'does-not-exist'" in result.stdout
    assert state.mutations == []


def test_categories_are_resolved_and_attached(prism):
    server, state = prism
    result = run_playbook(server, "vm_categories.yml",
                          {"vm_names": ["lab-db-01"], "categories": ["DR-Tier:PP-NEARSYNC-15M", "Environment:Lab"]})
    assert result.returncode == 0, result.stdout + result.stderr
    assert {c["extId"] for c in vm(state, "lab-db-01")["categories"]} == {c["extId"] for c in state.categories}


def test_unknown_category_fails_before_any_change(prism):
    server, state = prism
    result = run_playbook(server, "vm_categories.yml", {"vm_names": ["lab-db-01"], "categories": ["DR-Tier:Gold"]})
    assert result.returncode != 0
    assert "Unknown categories" in result.stdout
    assert state.mutations == []


def test_inventory_report_paginates(prism, tmp_path):
    server, _ = prism
    report = tmp_path / "inventory.csv"
    result = run_playbook(server, "vm_inventory_report.yml", {"report_path": str(report), "page_size": 2})
    assert result.returncode == 0, result.stdout + result.stderr
    rows = list(csv.DictReader(report.open()))
    assert [r["name"] for r in rows] == ["lab-app-01", "lab-db-01", "lab-web-01"]
    assert rows[1]["vcpus"] == "4" and rows[1]["memory_gib"] == "16.0"
