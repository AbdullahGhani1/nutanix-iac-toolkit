from pathlib import Path

from ntnx_report.cli import load_fixtures, main
from ntnx_report.report import Thresholds, build_report, to_csv, to_markdown, vm_vcpus

LAB = Path(__file__).resolve().parents[1] / "examples" / "lab"


def lab_report():
    return {r.name: r for r in build_report(*load_fixtures(LAB))}


def test_prism_central_is_excluded():
    assert set(lab_report()) == {"DC1-AHV-PROD", "DC2-AHV-DR"}


def test_host_capacity_and_powered_on_allocation():
    dc1 = lab_report()["DC1-AHV-PROD"]
    assert (dc1.hosts, dc1.physical_cores, dc1.memory_gib) == (3, 96, 1536.0)
    assert (dc1.vms, dc1.vms_powered_on) == (4, 3)  # the OFF template is not counted as allocated
    assert dc1.vcpu_allocated == 16 + 8 + 4
    assert dc1.memory_allocated_gib == 128 + 32 + 8
    assert dc1.status == "WARNING"  # one unresolved warning; the resolved one is ignored
    assert dc1.warning_alerts == 1


def test_overcommitted_cluster_is_critical():
    dc2 = lab_report()["DC2-AHV-DR"]
    assert dc2.vcpu_ratio == 4.0  # 192 vCPU on 48 cores
    assert dc2.memory_allocated_percent == 91.7
    assert dc2.status == "CRITICAL"
    assert any("vCPU:pCore ratio" in f for f in dc2.findings)
    assert any("critical alert" in f for f in dc2.findings)


def test_thresholds_are_configurable():
    relaxed = Thresholds(
        vcpu_ratio_warning=6, vcpu_ratio_critical=8, memory_percent_warning=95, memory_percent_critical=99
    )
    reports = {r.name: r for r in build_report(*load_fixtures(LAB), thresholds=relaxed)}
    assert reports["DC2-AHV-DR"].findings == ["1 unresolved critical alert(s)"]


def test_vcpu_math_defaults_missing_fields_to_one():
    assert vm_vcpus({"numSockets": 2, "numCoresPerSocket": 4, "numThreadsPerCore": 2}) == 16
    assert vm_vcpus({}) == 1


def test_renderers_sort_critical_first():
    reports = build_report(*load_fixtures(LAB))
    assert reports[0].name == "DC2-AHV-DR"
    assert "| DC2-AHV-DR | CRITICAL |" in to_markdown(reports)
    assert to_csv(reports).splitlines()[0].startswith("name,status,hosts")


def test_cli_exit_code_flags_critical(tmp_path):
    out = tmp_path / "report.json"
    assert main(["--fixtures", str(LAB), "--format", "json", "--out", str(out)]) == 2
    assert '"DC2-AHV-DR"' in out.read_text()


def test_cli_requires_credentials_for_live_mode(monkeypatch):
    monkeypatch.delenv("NUTANIX_PASSWORD", raising=False)
    assert main(["--pc", "https://pc.invalid:9440", "--username", "viewer"]) == 1
