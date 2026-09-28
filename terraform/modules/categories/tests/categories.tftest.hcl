mock_provider "nutanix" {}

variables {
  categories = {
    Environment = ["Lab", "Production"]
    AppTier     = ["Web"]
  }
}

run "one_category_per_key_value_pair" {
  command = plan

  assert {
    condition     = length(nutanix_category_v2.this) == 3
    error_message = "Expected one category resource per key/value pair."
  }

  assert {
    condition     = nutanix_category_v2.this["Environment:Production"].key == "Environment" && nutanix_category_v2.this["Environment:Production"].value == "Production"
    error_message = "Category key/value were not mapped from the input map."
  }
}
