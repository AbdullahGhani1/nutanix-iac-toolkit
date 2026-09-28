output "cluster_ext_id" {
  value = local.cluster_ext_id
}

output "subnet_ext_ids" {
  value = { for k, m in module.subnets : k => m.ext_id }
}

output "vm_ext_ids" {
  value = { for k, m in module.vms : k => m.ext_id }
}

output "category_ext_ids" {
  value = module.categories.ext_ids
}
