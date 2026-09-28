"""ntnx-report: Prism Central v4 capacity and health report.

Exit codes: 0 all clusters OK/WARNING, 2 at least one CRITICAL (so a scheduled
job can fail loudly), 1 on connection or API errors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .client import DEFAULT_VERSIONS, PrismClient, PrismError
from .report import Thresholds, build_report, to_csv, to_json, to_markdown

RENDERERS = {"md": to_markdown, "json": to_json, "csv": to_csv}


def load_fixtures(directory: Path) -> tuple[list, list, list, list]:
    def read(name: str) -> list:
        path = directory / f"{name}.json"
        if not path.exists():
            return []
        payload = json.loads(path.read_text())
        return payload.get("data", payload) if isinstance(payload, dict) else payload

    return read("clusters"), read("hosts"), read("vms"), read("alerts")


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="ntnx-report", description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--pc", help="Prism Central URL, e.g. https://pc.example.local:9440")
    src.add_argument("--fixtures", type=Path, help="Directory with clusters/hosts/vms/alerts JSON (offline mode)")
    p.add_argument("--username", default=os.environ.get("NUTANIX_USERNAME", ""))
    p.add_argument("--insecure", action="store_true", help="Skip TLS verification (lab only)")
    p.add_argument("--ca-bundle", help="CA bundle for the Prism Central certificate")
    p.add_argument("--api-version", default="v4.0", help="v4 minor version for all namespaces (default v4.0)")
    p.add_argument("--format", choices=sorted(RENDERERS), default="md")
    p.add_argument("--out", type=Path, help="Write to file instead of stdout")
    p.add_argument("--vcpu-ratio-warning", type=float, default=3.0)
    p.add_argument("--vcpu-ratio-critical", type=float, default=4.0)
    p.add_argument("--memory-warning", type=float, default=80.0)
    p.add_argument("--memory-critical", type=float, default=90.0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        if args.fixtures:
            clusters, hosts, vms, alerts = load_fixtures(args.fixtures)
        else:
            password = os.environ.get("NUTANIX_PASSWORD", "")
            if not args.username or not password:
                print("Set --username/NUTANIX_USERNAME and NUTANIX_PASSWORD", file=sys.stderr)
                return 1
            client = PrismClient(
                args.pc,
                args.username,
                password,
                verify_tls=False if args.insecure else (args.ca_bundle or True),
                versions={k: args.api_version for k in DEFAULT_VERSIONS},
            )
            clusters, hosts, vms, alerts = client.clusters(), client.hosts(), client.vms(), client.unresolved_alerts()
    except (PrismError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    thresholds = Thresholds(
        args.vcpu_ratio_warning, args.vcpu_ratio_critical, args.memory_warning, args.memory_critical
    )
    reports = build_report(clusters, hosts, vms, alerts, thresholds)
    output = RENDERERS[args.format](reports)
    if args.out:
        args.out.write_text(output)
    else:
        sys.stdout.write(output)
    return 2 if any(r.status == "CRITICAL" for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
