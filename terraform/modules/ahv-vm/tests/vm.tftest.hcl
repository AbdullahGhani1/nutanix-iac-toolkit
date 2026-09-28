mock_provider "nutanix" {}

variables {
  name              = "lab-db-01"
  cluster_ext_id    = "00000000-0000-0000-0000-000000000001"
  boot_image_ext_id = "00000000-0000-0000-0000-000000000002"
  subnet_ext_ids    = ["00000000-0000-0000-0000-000000000003"]
  memory_gib        = 16
  num_sockets       = 2
}

run "sizes_and_nics" {
  command = plan

  assert {
    condition     = nutanix_virtual_machine_v2.this.memory_size_bytes == 16 * 1024 * 1024 * 1024
    error_message = "memory_gib must be converted to bytes."
  }

  assert {
    condition     = length(nutanix_virtual_machine_v2.this.nics) == 1 && length(nutanix_virtual_machine_v2.this.disks) == 1
    error_message = "Expected one NIC and only the boot disk."
  }

  assert {
    condition     = length(nutanix_virtual_machine_v2.this.boot_config[0].legacy_boot) == 1
    error_message = "Legacy boot is the default."
  }
}

run "data_disks_follow_boot_disk" {
  command = plan

  variables {
    data_disks_gib           = [100, 200]
    storage_container_ext_id = "00000000-0000-0000-0000-000000000004"
    uefi                     = true
  }

  assert {
    condition     = [for d in nutanix_virtual_machine_v2.this.disks : d.disk_address[0].index] == [0, 1, 2]
    error_message = "Data disks must use SCSI indexes after the boot disk."
  }

  assert {
    condition     = nutanix_virtual_machine_v2.this.disks[2].backing_info[0].vm_disk[0].disk_size_bytes == 200 * 1024 * 1024 * 1024
    error_message = "Data disk size must be converted to bytes."
  }
}

run "data_disks_require_container" {
  command = plan

  variables {
    data_disks_gib = [50]
  }

  expect_failures = [nutanix_virtual_machine_v2.this]
}
