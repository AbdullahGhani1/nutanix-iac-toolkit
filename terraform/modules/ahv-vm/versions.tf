terraform {
  required_version = ">= 1.5"
  required_providers {
    nutanix = {
      source  = "nutanix/nutanix"
      version = "~> 2.4"
    }
  }
}
