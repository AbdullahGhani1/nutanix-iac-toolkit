locals {
  gib = 1024 * 1024 * 1024
}

resource "nutanix_virtual_machine_v2" "this" {
  name                 = var.name
  description          = var.description
  num_sockets          = var.num_sockets
  num_cores_per_socket = var.num_cores_per_socket
  memory_size_bytes    = var.memory_gib * local.gib
  power_state          = var.power_state

  cluster {
    ext_id = var.cluster_ext_id
  }

  disks {
    disk_address {
      bus_type = "SCSI"
      index    = 0
    }
    backing_info {
      vm_disk {
        data_source {
          reference {
            image_reference {
              image_ext_id = var.boot_image_ext_id
            }
          }
        }
      }
    }
  }

  dynamic "disks" {
    for_each = var.data_disks_gib
    content {
      disk_address {
        bus_type = "SCSI"
        index    = disks.key + 1
      }
      backing_info {
        vm_disk {
          disk_size_bytes = disks.value * local.gib
          storage_container {
            ext_id = var.storage_container_ext_id
          }
        }
      }
    }
  }

  dynamic "nics" {
    for_each = var.subnet_ext_ids
    content {
      nic_network_info {
        virtual_ethernet_nic_network_info {
          nic_type  = "NORMAL_NIC"
          vlan_mode = "ACCESS"
          subnet {
            ext_id = nics.value
          }
        }
      }
    }
  }

  dynamic "categories" {
    for_each = var.category_ext_ids
    content {
      ext_id = categories.value
    }
  }

  boot_config {
    dynamic "legacy_boot" {
      for_each = var.uefi ? [] : [1]
      content {
        boot_order = ["DISK", "CDROM", "NETWORK"]
      }
    }
    dynamic "uefi_boot" {
      for_each = var.uefi ? [1] : []
      content {}
    }
  }

  dynamic "guest_customization" {
    # Only the null check is unmarked; the user-data itself stays sensitive.
    for_each = nonsensitive(var.cloud_init_user_data == null) ? [] : [1]
    content {
      config {
        cloud_init {
          cloud_init_script {
            user_data {
              value = base64encode(var.cloud_init_user_data)
            }
          }
        }
      }
    }
  }

  lifecycle {
    precondition {
      condition     = length(var.data_disks_gib) == 0 || var.storage_container_ext_id != null
      error_message = "storage_container_ext_id is required when data_disks_gib is set."
    }
    # Guest customization is applied once at creation; the boot disk is cloned from the image once.
    ignore_changes = [guest_customization, disks[0].backing_info[0].vm_disk[0].data_source]
  }
}
