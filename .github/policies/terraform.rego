package main

# Deny resources without tags
deny[msg] {
  input.resource.aws_instance[_].tags == {}
  msg = "All AWS instances must have tags"
}

# Deny S3 buckets without encryption
deny[msg] {
  input.resource.aws_s3_bucket[_]
  not input.resource.aws_s3_bucket[_].server_side_encryption_configuration
  msg = "S3 buckets must have server-side encryption"
}

# For GCP, similar rules
deny[msg] {
  input.resource.google_storage_bucket[_]
  not input.resource.google_storage_bucket[_].encryption
  msg = "GCS buckets must have encryption"
}