variable "insecure" {
  description = "Skip TLS verification of Prism Central (lab/CE self-signed certificates only)"
  type        = bool
  default     = false
}

variable "cluster_name" {
  description = "Prism Element cluster registered to Prism Central"
  type        = string
}

variable "storage_container_name" {
  type    = string
  default = "default-container"
}

variable "image" {
  description = "Cloud image imported once and cloned into every VM boot disk"
  type = object({
    name = string
    url  = string
  })
  default = {
    name = "ubuntu-24.04-cloudimg"
    url  = "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"
  }
}

variable "subnets" {
  description = "VLAN subnets keyed by name"
  type = map(object({
    vlan_id = number
    ipam = optional(object({
      network       = string
      prefix_length = number
      gateway       = string
      pool_start    = string
      pool_end      = string
      dns_servers   = optional(list(string), [])
      domain_name   = optional(string)
    }))
  }))
}

variable "categories" {
  type = map(list(string))
  default = {
    Environment = ["Lab", "Production"]
    AppTier     = ["Web", "App", "DB"]
    "DR-Tier"   = ["PP-NEARSYNC-15M", "PP-ASYNC-1H", "PP-ASYNC-4H"]
  }
}

variable "vms" {
  description = "VMs keyed by name"
  type = map(object({
    subnet         = string
    sockets        = optional(number, 1)
    cores          = optional(number, 2)
    memory_gib     = optional(number, 4)
    data_disks_gib = optional(list(number), [])
    categories     = optional(list(string), [])
    power_state    = optional(string, "ON")
  }))
}

variable "ssh_authorized_keys" {
  description = "Public keys injected by cloud-init for the admin user"
  type        = list(string)
  default     = []
}
