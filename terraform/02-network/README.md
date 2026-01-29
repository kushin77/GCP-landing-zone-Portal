# Network Layer (02)

Establishes secure network infrastructure with VPCs, subnets, firewalls, and connectivity.

## Components

- **vpc/**: VPC network and subnet definitions
- **firewall/**: Firewall rules and policies
- **nat/**: Cloud NAT configuration for outbound internet access

## Deploy

```bash
cd terraform
terraform -chdir=02-network init
terraform -chdir=02-network plan
terraform -chdir=02-network apply
```

## Requirements

- Completed: Layer 01 (Foundation)
- GCP Project with APIs enabled
- Terraform state bucket configured

## Resources Created

- VPC Network (prod-vpc, 10.0.0.0/16)
- Subnets (3 per AZ for HA)
- Firewall rules (internal, health checks, outbound)
- Cloud NAT (for outbound internet)

