data "nutanix_clusters_v2" "target" {
  filter = "name eq '${var.cluster_name}'"
}

locals {
  cluster_ext_id = one([
    for c in data.nutanix_clusters_v2.target.cluster_entities : c.ext_id
    if !contains(c.config[0].cluster_function, "PRISM_CENTRAL")
  ])
}

data "nutanix_storage_containers_v2" "target" {
  filter = "name eq '${var.storage_container_name}' and clusterExtId eq '${local.cluster_ext_id}'"
}

resource "nutanix_images_v2" "base" {
  name                     = var.image.name
  type                     = "DISK_IMAGE"
  cluster_location_ext_ids = [local.cluster_ext_id]
  source {
    url_source {
      url = var.image.url
    }
  }
}

module "subnets" {
  source         = "../../modules/ahv-subnet"
  for_each       = var.subnets
  name           = each.key
  cluster_ext_id = local.cluster_ext_id
  vlan_id        = each.value.vlan_id
  ipam           = each.value.ipam
}

module "categories" {
  source     = "../../modules/categories"
  categories = var.categories
}

module "vms" {
  source                   = "../../modules/ahv-vm"
  for_each                 = var.vms
  name                     = each.key
  cluster_ext_id           = local.cluster_ext_id
  num_sockets              = each.value.sockets
  num_cores_per_socket     = each.value.cores
  memory_gib               = each.value.memory_gib
  boot_image_ext_id        = nutanix_images_v2.base.id
  data_disks_gib           = each.value.data_disks_gib
  storage_container_ext_id = one(data.nutanix_storage_containers_v2.target.storage_containers[*].container_ext_id)
  subnet_ext_ids           = [module.subnets[each.value.subnet].ext_id]
  category_ext_ids         = [for c in each.value.categories : module.categories.ext_ids[c]]
  power_state              = each.value.power_state
  cloud_init_user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    hostname            = each.key
    ssh_authorized_keys = var.ssh_authorized_keys
  })
}
