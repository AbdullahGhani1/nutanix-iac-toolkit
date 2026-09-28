resource "nutanix_subnet_v2" "this" {
  name              = var.name
  description       = var.description
  cluster_reference = var.cluster_ext_id
  subnet_type       = "VLAN"
  network_id        = var.vlan_id

  dynamic "ip_config" {
    for_each = var.ipam == null ? [] : [var.ipam]
    content {
      ipv4 {
        ip_subnet {
          ip {
            value = ip_config.value.network
          }
          prefix_length = ip_config.value.prefix_length
        }
        default_gateway_ip {
          value = ip_config.value.gateway
        }
        pool_list {
          start_ip {
            value = ip_config.value.pool_start
          }
          end_ip {
            value = ip_config.value.pool_end
          }
        }
      }
    }
  }

  dynamic "dhcp_options" {
    for_each = var.ipam == null ? [] : [var.ipam]
    content {
      domain_name = dhcp_options.value.domain_name
      dynamic "domain_name_servers" {
        for_each = dhcp_options.value.dns_servers
        content {
          ipv4 {
            value = domain_name_servers.value
          }
        }
      }
    }
  }
}
