output "ext_id" {
  description = "extId of the subnet, used to attach VM NICs"
  value       = nutanix_subnet_v2.this.id
}

output "name" {
  value = nutanix_subnet_v2.this.name
}
