variable "categories" {
  description = "Map of category key => list of values, e.g. { Environment = [\"Prod\", \"Dev\"] }"
  type        = map(list(string))
}

variable "description" {
  type    = string
  default = "Managed by Terraform"
}
