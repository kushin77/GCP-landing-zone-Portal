#!/usr/bin/env python3
"""
Direct test of git-rca-workspace services without backend dependencies.
"""

import sys
import os
import asyncio
import importlib.util

# Add git-rca-workspace to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git-rca-workspace', 'src'))

async def test_service_directly(service_name: str):
    """Test a specific service directly."""
    try:
        # Import the service module
        spec = importlib.util.spec_from_file_location(
            service_name,
            f"git-rca-workspace/src/services/{service_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the service class (usually the only class in the module)
        service_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and not attr_name.startswith('_'):
                service_class = attr
                break

        if not service_class:
            print(f"❌ No service class found in {service_name}")
            return False

        # Instantiate the service
        service_instance = service_class()

        # Test different method patterns
        result = None

        if hasattr(service_instance, 'analyze_investigation'):
            print(f"  Testing analyze_investigation method...")
            investigation = {
                "id": "test-123",
                "title": "Test Issue",
                "description": "This is a test issue for RCA analysis",
                "severity": "medium"
            }
            events = ["event1", "event2"]
            result = service_instance.analyze_investigation(investigation, events)

        elif hasattr(service_instance, 'analyze_incident'):
            print(f"  Testing analyze_incident method...")
            result = await service_instance.analyze_incident("test-123", "Test issue description")

        elif hasattr(service_instance, 'analyze_events'):
            print(f"  Testing analyze_events method...")
            result = await service_instance.analyze_events(["event1", "event2"])

        elif hasattr(service_instance, 'analyze_incident_across_repos'):
            print(f"  Testing analyze_incident_across_repos method...")
            result = service_instance.analyze_incident_across_repos(1, "test-repo")

        else:
            print(f"❌ No compatible analyze method found in {service_name}")
            return False

        if result:
            print(f"✅ {service_name} analysis successful: {type(result)}")
            return True
        else:
            print(f"❌ {service_name} returned empty result")
            return False

    except Exception as e:
        print(f"❌ {service_name} failed: {str(e)}")
        return False

async def main():
    """Test available services."""
    print("Testing git-rca-workspace services directly...")

    # List of services that were available in the discovery
    available_services = [
        'prometheus_metrics',
        'vulnerability_scanner',
        'default_playbooks',
        'remediation_playbooks',
        'visualization_service',
        'rca_dashboard_service',
        'rbac_service',
        'token_rotation_service',
        'api_key_manager'
    ]

    successful_services = 0
    total_services = len(available_services)

    for service_name in available_services:
        print(f"\nTesting {service_name}...")
        if await test_service_directly(service_name):
            successful_services += 1

    print(f"\n{'='*50}")
    print(f"Results: {successful_services}/{total_services} services working")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())