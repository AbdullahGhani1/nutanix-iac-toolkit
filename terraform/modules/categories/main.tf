locals {
  pairs = {
    for pair in flatten([
      for key, values in var.categories : [for value in values : { key = key, value = value }]
    ]) : "${pair.key}:${pair.value}" => pair
  }
}

resource "nutanix_category_v2" "this" {
  for_each    = local.pairs
  key         = each.value.key
  value       = each.value.value
  description = var.description
}
