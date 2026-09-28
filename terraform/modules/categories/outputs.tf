output "ext_ids" {
  description = "Map of \"Key:Value\" => category extId"
  value       = { for k, c in nutanix_category_v2.this : k => c.id }
}
