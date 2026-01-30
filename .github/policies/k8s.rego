package main

# Deny deployments without resource limits
deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.resources.limits
  msg = sprintf("Container %s must have resource limits", [container.name])
}

# Deny deployments without security context
deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.securityContext
  msg = "Deployment must have security context"
}

# Deny containers running as root
deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.securityContext.runAsNonRoot
  msg = sprintf("Container %s must run as non-root", [container.name])
}