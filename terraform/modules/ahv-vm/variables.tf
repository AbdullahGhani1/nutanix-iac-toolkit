variable "name" {
  type = string
}

variable "description" {
  type    = string
  default = "Managed by Terraform"
}

variable "cluster_ext_id" {
  type = string
}

variable "num_sockets" {
  type    = number
  default = 1
}

variable "num_cores_per_socket" {
  type    = number
  default = 2
}

variable "memory_gib" {
  type    = number
  default = 4
  validation {
    condition     = var.memory_gib >= 1
    error_message = "memory_gib must be at least 1."
  }
}

variable "boot_image_ext_id" {
  description = "Image cloned into the boot disk (SCSI 0)"
  type        = string
}

variable "data_disks_gib" {
  description = "Additional empty SCSI disks, in GiB"
  type        = list(number)
  default     = []
}

variable "storage_container_ext_id" {
  description = "Storage container for additional data disks"
  type        = string
  default     = null
}

variable "subnet_ext_ids" {
  description = "One NIC is created per subnet, in order"
  type        = list(string)
}

variable "category_ext_ids" {
  description = "Categories attached to the VM (used by protection and security policies)"
  type        = list(string)
  default     = []
}

variable "cloud_init_user_data" {
  description = "Plain-text cloud-init user-data; null to skip guest customization"
  type        = string
  default     = null
  sensitive   = true
}

variable "uefi" {
  type    = bool
  default = false
}

variable "power_state" {
  type    = string
  default = "ON"
  validation {
    condition     = contains(["ON", "OFF"], var.power_state)
    error_message = "power_state must be ON or OFF."
  }
}
