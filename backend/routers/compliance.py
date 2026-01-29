"""
Compliance API router.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from models.schemas import ComplianceFramework, ComplianceStatus
from services.compliance_service import compliance_service

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


@router.get("/status", response_model=ComplianceStatus)
async def get_compliance_status(
    framework: ComplianceFramework = Query(ComplianceFramework.NIST_800_53),
):
    """Get overall compliance status for a framework."""
    status = await compliance_service.get_compliance_status(framework)
    return status


@router.get("/frameworks")
async def list_frameworks():
    """List all supported compliance frameworks."""
    return {
        "frameworks": [
            {
                "id": ComplianceFramework.NIST_800_53,
                "name": "NIST 800-53",
                "description": "NIST Special Publication 800-53 Security Controls",
                "version": "Rev 5",
            },
            {
                "id": ComplianceFramework.FEDRAMP,
                "name": "FedRAMP",
                "description": "Federal Risk and Authorization Management Program",
                "version": "Latest",
            },
            {
                "id": ComplianceFramework.CIS,
                "name": "CIS Benchmarks",
                "description": "Center for Internet Security GCP Benchmarks",
                "version": "1.3.0",
            },
            {
                "id": ComplianceFramework.PCI_DSS,
                "name": "PCI DSS",
                "description": "Payment Card Industry Data Security Standard",
                "version": "4.0",
            },
            {
                "id": ComplianceFramework.HIPAA,
                "name": "HIPAA",
                "description": "Health Insurance Portability and Accountability Act",
                "version": "Current",
            },
            {
                "id": ComplianceFramework.SOC2,
                "name": "SOC 2",
                "description": "Service Organization Control 2",
                "version": "Type II",
            },
        ]
    }


@router.get("/controls/{control_id}")
async def get_control_details(
    control_id: str, framework: ComplianceFramework = Query(ComplianceFramework.NIST_800_53)
):
    """Get detailed information about a specific control."""
    status = await compliance_service.get_compliance_status(framework)

    control = next((c for c in status.findings if c.id == control_id), None)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    return control


@router.post("/scan")
async def trigger_compliance_scan(
    framework: ComplianceFramework = Query(ComplianceFramework.NIST_800_53),
):
    """Trigger a new compliance scan."""
    # In production, this would trigger an async scan job
    return {
        "scan_id": f"scan-{framework.value}-{datetime.utcnow().timestamp()}",
        "framework": framework,
        "status": "initiated",
        "estimated_duration": "5-10 minutes",
    }


@router.get("/reports")
async def list_compliance_reports():
    """List available compliance reports."""

    return {
        "reports": [
            {
                "id": "report-001",
                "framework": ComplianceFramework.NIST_800_53,
                "date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "score": 99.1,
                "status": "passed",
            },
            {
                "id": "report-002",
                "framework": ComplianceFramework.FEDRAMP,
                "date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "score": 95.0,
                "status": "passed",
            },
        ]
    }
