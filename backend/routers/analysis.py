"""Analysis router for RCA (Root Cause Analysis) functionality.

Provides endpoints for intelligent issue analysis and automated remediation.
"""
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException

from services.rca_analysis_service import rca_service

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/rca", response_model=Dict[str, Any])
async def perform_root_cause_analysis(issue_data: Dict[str, Any]):
    """Perform root cause analysis on an issue.

    Accepts issue data and returns analysis results with recommendations.
    """
    try:
        return await rca_service.analyze_issue(issue_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/services", response_model=List[Dict[str, Any]])
async def get_available_services():
    """Get list of available RCA analysis services."""
    try:
        return await rca_service.get_service_capabilities()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get services: {str(e)}")


@router.post("/rca/batch", response_model=List[Dict[str, Any]])
async def perform_batch_analysis(issues: List[Dict[str, Any]]):
    """Perform root cause analysis on multiple issues.

    Accepts a list of issues and returns analysis results for each.
    """
    try:
        results = []
        for issue in issues:
            result = await rca_service.analyze_issue(issue)
            results.append(result)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")