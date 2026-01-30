terraform {
  backend "gcs" {
    bucket  = "lz-terraform-state-bucket"
    prefix  = "terraform/state"
  }
}