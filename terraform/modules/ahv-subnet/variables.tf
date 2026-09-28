variable "name" {
  description = "Subnet name as shown in Prism Central"
  type        = string
}

variable "description" {
  description = "Free-text description"
  type        = string
  default     = "Managed by Terraform"
}

variable "cluster_ext_id" {
  description = "extId of the AHV cluster that owns the VLAN"
  type        = string
}

variable "vlan_id" {
  description = "802.1Q VLAN ID trunked to the AHV hosts"
  type        = number
  validation {
    condition     = var.vlan_id >= 0 && var.vlan_id <= 4094
    error_message = "vlan_id must be between 0 and 4094."
  }
}

variable "ipam" {
  description = "Optional AHV IPAM. Leave null for a VLAN without Nutanix-managed DHCP (e.g. external DHCP)."
  type = object({
    network       = string
    prefix_length = number
    gateway       = string
    pool_start    = string
    pool_end      = string
    dns_servers   = optional(list(string), [])
    domain_name   = optional(string)
  })
  default = null
}
