# Onboarding: Using git-rca-workspace Integration

This guide explains how to onboard new projects and resources using the git-rca-workspace integration with the GCP Landing Zone Portal.

## Overview

The git-rca-workspace repository serves as the source of truth for infrastructure and service definitions. The Portal automatically discovers and syncs resources from this repository to provide a unified view.

## Prerequisites

- Access to the git-rca-workspace repository
- GCP project permissions for the target environment
- Portal access with appropriate roles

## Onboarding Steps

### 1. Prepare Repository Structure

Ensure your git-rca-workspace follows the expected structure:

```
git-rca-workspace/
├── services/{team}/{service}/terraform/*    # Service definitions
├── infrastructure/{project}/k8s/{cluster}/manifests/*  # Kubernetes resources
└── infrastructure/{project}/storage/*       # Storage configurations
```

### 2. Define Resources

Add your resources following the mapping guidelines in [portal_mapping.md](portal_mapping.md).

### 3. Trigger Discovery

The Portal runs discovery hourly. To manually trigger:

```bash
# Via API (if available)
curl -X POST http://localhost:8080/api/v1/discovery/sync
```

### 4. Verify Onboarding

Check the Portal dashboard to confirm resources appear correctly.

## Troubleshooting

- If resources don't appear, check the discovery logs
- Ensure proper naming conventions are followed
- Verify GCP permissions for the service account

## Related Documentation

- [Portal Mapping](portal_mapping.md)
- [Discovery Service](../backend/discovery/README.md)</content>
<parameter name="filePath">E:\Coding\Dad\GCP-landing-zone-Portal\docs\onboarding-git-rca-workspace.md