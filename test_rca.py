#!/usr/bin/env python3
"""
Test script for RCA analysis functionality.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.rca_analysis_service import rca_service

async def test_rca_analysis():
    """Test the RCA analysis service directly."""
    print("Testing RCA Analysis Service...")

    # First, check what services are available
    print("Discovering available services...")
    try:
        services = await rca_service.get_service_capabilities()
        print(f"Found {len(services)} services:")
        for service in services:
            print(f"  - {service['name']}: {service['status']} ({service.get('error', 'no error')})")
    except Exception as e:
        print(f"Failed to get services: {e}")
        return False

    # Sample issue data
    issue_data = {
        "id": "ISSUE-123",
        "title": "High CPU usage on production servers",
        "description": "Production servers experiencing 90%+ CPU utilization for the past 2 hours",
        "severity": "high",
        "category": "performance",
        "affected_services": ["web-frontend", "api-gateway", "database"],
        "timestamp": "2026-01-30T12:00:00Z"
    }

    print("\nTesting analysis with sample issue...")
    try:
        result = await rca_service.analyze_issue(issue_data)
        print("✅ RCA Analysis completed successfully!")
        print(f"Services used: {result.get('services_used', 0)}")
        print(f"Results: {len(result.get('results', []))}")

        # Print top findings
        top_findings = result.get('top_findings', [])
        if top_findings:
            print("\nTop Findings:")
            for finding in top_findings[:3]:
                confidence = finding.get('confidence', 0) * 100
                print(f"  - {finding.get('service')}: {confidence:.0f}% confidence")

        # Print recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations: {len(recommendations)}")
            for rec in recommendations[:3]:
                print(f"  - {rec.get('description', 'No description')}")

        return True

    except Exception as e:
        print(f"❌ RCA Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rca_analysis())
    sys.exit(0 if success else 1)