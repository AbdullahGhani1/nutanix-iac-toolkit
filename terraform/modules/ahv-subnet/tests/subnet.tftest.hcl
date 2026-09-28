mock_provider "nutanix" {}

variables {
  name           = "vlan-110-app"
  cluster_ext_id = "00000000-0000-0000-0000-000000000001"
  vlan_id        = 110
}

run "vlan_without_ipam" {
  command = plan

  assert {
    condition     = nutanix_subnet_v2.this.subnet_type == "VLAN" && nutanix_subnet_v2.this.network_id == 110
    error_message = "Subnet must be a VLAN subnet on the requested VLAN ID."
  }

  assert {
    condition     = length(nutanix_subnet_v2.this.ip_config) == 0
    error_message = "No IPAM block expected when ipam is null."
  }
}

run "vlan_with_ipam" {
  command = plan

  variables {
    ipam = {
      network       = "10.10.110.0"
      prefix_length = 24
      gateway       = "10.10.110.1"
      pool_start    = "10.10.110.50"
      pool_end      = "10.10.110.199"
      dns_servers   = ["10.10.0.10", "10.10.0.11"]
    }
  }

  assert {
    condition     = nutanix_subnet_v2.this.ip_config[0].ipv4[0].default_gateway_ip[0].value == "10.10.110.1"
    error_message = "Gateway was not set from ipam."
  }

  assert {
    condition     = length(nutanix_subnet_v2.this.dhcp_options[0].domain_name_servers) == 2
    error_message = "Both DNS servers should be configured."
  }
}

run "rejects_invalid_vlan" {
  command = plan

  variables {
    vlan_id = 5000
  }

  expect_failures = [var.vlan_id]
}
