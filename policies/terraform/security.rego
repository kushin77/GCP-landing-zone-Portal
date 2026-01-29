package main

# Deny if public access is enabled on any storage bucket
deny[msg] {
    input.resource_type == "google_storage_bucket"
    input.attributes.public_access_prevention != "enforced"
    msg = sprintf("Storage bucket %v must have public_access_prevention set to 'enforced'", [input.name])
}

# Warn if deletion_protection is false
warn[msg] {
    input.resource_type == "google_sql_database_instance"
    input.attributes.deletion_protection == false
    msg = sprintf("SQL instance %v should have deletion_protection enabled", [input.name])
}
