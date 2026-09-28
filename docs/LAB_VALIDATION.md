# Lab validation log

Fill in this log while running the toolkit against a real cluster (for example Nutanix Community Edition). Record
what actually happened; leave rows empty until they are done.

## Environment

| Item | Value |
|---|---|
| Hardware / nested host | |
| AOS / AHV version | |
| Prism Central version | |
| Terraform / provider version | |
| Ansible core version | |
| Date | |

## Results

| # | Step | Command | Result | Evidence (screenshot, output file) |
|---|---|---|---|---|
| 1 | Create VLAN subnets with IPAM | `terraform apply` (lab) | | |
| 2 | Create categories | `terraform apply` (lab) | | |
| 3 | Import cloud image and create VMs with cloud-init | `terraform apply` (lab) | | |
| 4 | SSH into a VM with the injected key | `ssh nxadmin@<ip>` | | |
| 5 | Graceful shutdown and power-on | `vm_power.yml` | | |
| 6 | Re-run power-on (idempotency) | `vm_power.yml` | | |
| 7 | Tag a VM with a DR-Tier category, check the protection policy picks it up | `vm_categories.yml` | | |
| 8 | Export the VM inventory | `vm_inventory_report.yml` | | |
| 9 | Capacity and health report | `ntnx-report --pc ...` | | |
| 10 | Destroy the lab resources | `terraform destroy` | | |

## Issues found and fixes

| Issue | Root cause | Fix / commit |
|---|---|---|
| | | |
