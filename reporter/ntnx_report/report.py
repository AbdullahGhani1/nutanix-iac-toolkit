"""Per-cluster allocation, capacity and alert summary built from v4 inventory.

Figures are allocation-based (what VMs are configured with), not measured
utilization. They answer "how much of this cluster has been handed out and
what is alerting", which is what capacity reviews and change approvals ask.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field

GIB = 1024**3


@dataclass(frozen=True)
class Thresholds:
    vcpu_ratio_warning: float = 3.0
    vcpu_ratio_critical: float = 4.0
    memory_percent_warning: float = 80.0
    memory_percent_critical: float = 90.0


@dataclass
class ClusterReport:
    ext_id: str
    name: str
    hosts: int = 0
    physical_cores: int = 0
    memory_gib: float = 0.0
    vms: int = 0
    vms_powered_on: int = 0
    vcpu_allocated: int = 0
    memory_allocated_gib: float = 0.0
    vcpu_ratio: float = 0.0
    memory_allocated_percent: float = 0.0
    critical_alerts: int = 0
    warning_alerts: int = 0
    status: str = "OK"
    findings: list[str] = field(default_factory=list)


def is_prism_central(cluster: dict) -> bool:
    functions = ((cluster.get("config") or {}).get("clusterFunction")) or []
    return "PRISM_CENTRAL" in functions


def vm_vcpus(vm: dict) -> int:
    return (
        int(vm.get("numSockets") or 1) * int(vm.get("numCoresPerSocket") or 1) * int(vm.get("numThreadsPerCore") or 1)
    )


def build_report(clusters, hosts, vms, alerts, thresholds: Thresholds | None = None) -> list[ClusterReport]:
    t = thresholds or Thresholds()
    reports = {
        c["extId"]: ClusterReport(ext_id=c["extId"], name=c.get("name") or c["extId"])
        for c in clusters
        if c.get("extId") and not is_prism_central(c)
    }

    for host in hosts:
        report = reports.get(((host.get("cluster") or {}).get("uuid")) or "")
        if report is None:
            continue
        report.hosts += 1
        report.physical_cores += int(host.get("numberOfCpuCores") or 0)
        report.memory_gib += (host.get("memorySizeBytes") or 0) / GIB

    for vm in vms:
        report = reports.get(((vm.get("cluster") or {}).get("extId")) or "")
        if report is None:
            continue
        report.vms += 1
        if vm.get("powerState") == "ON":
            report.vms_powered_on += 1
            report.vcpu_allocated += vm_vcpus(vm)
            report.memory_allocated_gib += (vm.get("memorySizeBytes") or 0) / GIB

    for alert in alerts:
        if alert.get("isResolved"):
            continue
        report = reports.get(alert.get("clusterUUID") or "")
        if report is None:
            continue
        if alert.get("severity") == "CRITICAL":
            report.critical_alerts += 1
        elif alert.get("severity") == "WARNING":
            report.warning_alerts += 1

    for r in reports.values():
        r.memory_gib = round(r.memory_gib, 1)
        r.memory_allocated_gib = round(r.memory_allocated_gib, 1)
        r.vcpu_ratio = round(r.vcpu_allocated / r.physical_cores, 2) if r.physical_cores else 0.0
        r.memory_allocated_percent = round(100 * r.memory_allocated_gib / r.memory_gib, 1) if r.memory_gib else 0.0
        _evaluate(r, t)

    return sorted(reports.values(), key=lambda r: ({"CRITICAL": 0, "WARNING": 1, "OK": 2}[r.status], r.name))


def _evaluate(r: ClusterReport, t: Thresholds) -> None:
    critical, warning = [], []
    if r.hosts == 0:
        warning.append("No hosts returned for this cluster; capacity figures are incomplete")
    if r.vcpu_ratio >= t.vcpu_ratio_critical:
        critical.append(f"vCPU:pCore ratio {r.vcpu_ratio} >= {t.vcpu_ratio_critical}")
    elif r.vcpu_ratio >= t.vcpu_ratio_warning:
        warning.append(f"vCPU:pCore ratio {r.vcpu_ratio} >= {t.vcpu_ratio_warning}")
    if r.memory_allocated_percent >= t.memory_percent_critical:
        critical.append(f"Memory allocated {r.memory_allocated_percent}% >= {t.memory_percent_critical}%")
    elif r.memory_allocated_percent >= t.memory_percent_warning:
        warning.append(f"Memory allocated {r.memory_allocated_percent}% >= {t.memory_percent_warning}%")
    if r.critical_alerts:
        critical.append(f"{r.critical_alerts} unresolved critical alert(s)")
    if r.warning_alerts:
        warning.append(f"{r.warning_alerts} unresolved warning alert(s)")
    r.findings = critical + warning
    r.status = "CRITICAL" if critical else "WARNING" if warning else "OK"


COLUMNS = [
    "name",
    "status",
    "hosts",
    "physical_cores",
    "memory_gib",
    "vms",
    "vms_powered_on",
    "vcpu_allocated",
    "vcpu_ratio",
    "memory_allocated_gib",
    "memory_allocated_percent",
    "critical_alerts",
    "warning_alerts",
]


def to_json(reports: list[ClusterReport]) -> str:
    return json.dumps([asdict(r) for r in reports], indent=2)


def to_csv(reports: list[ClusterReport]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS + ["findings"])
    for r in reports:
        writer.writerow([getattr(r, c) for c in COLUMNS] + ["; ".join(r.findings)])
    return buffer.getvalue()


def to_markdown(reports: list[ClusterReport]) -> str:
    lines = [
        "# Nutanix cluster capacity and health report",
        "",
        "Allocation-based figures for powered-on VMs; not measured utilization.",
        "",
        "| Cluster | Status | Hosts | Cores | vCPU | vCPU:pCore | RAM GiB | RAM alloc | Crit / Warn alerts |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in reports:
        lines.append(
            f"| {r.name} | {r.status} | {r.hosts} | {r.physical_cores} | {r.vcpu_allocated} | {r.vcpu_ratio} "
            f"| {r.memory_gib} | {r.memory_allocated_percent}% | {r.critical_alerts} / {r.warning_alerts} |"
        )
    flagged = [r for r in reports if r.findings]
    if flagged:
        lines += ["", "## Findings", ""]
        for r in flagged:
            lines += [f"### {r.name} ({r.status})", ""] + [f"- {f}" for f in r.findings] + [""]
    return "\n".join(lines).rstrip() + "\n"
