terraform {
  required_version = ">= 1.5"
  required_providers {
    nutanix = {
      source  = "nutanix/nutanix"
      version = "~> 2.4"
    }
  }
}

# Credentials come from the environment, never from files in this repo:
#   export NUTANIX_USERNAME=... NUTANIX_PASSWORD=... NUTANIX_ENDPOINT=pc.lab.local
provider "nutanix" {
  port     = 9440
  insecure = var.insecure
}
