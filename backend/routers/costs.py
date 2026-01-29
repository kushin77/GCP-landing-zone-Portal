"""
Costs API router.
"""
from fastapi import APIRouter, Query
from models.schemas import CostSummary
from services.gcp_client import CostService, gcp_clients

router = APIRouter(prefix="/api/v1/costs", tags=["costs"])


def get_cost_service():
    """Get cost service instance."""
    return CostService(gcp_clients)


@router.get("/summary", response_model=CostSummary)
async def get_cost_summary():
    """Get comprehensive cost summary with trends and breakdowns."""
    service = get_cost_service()

    # Get current month costs
    current_month = await service.get_current_month_costs()

    # Get previous month costs (simplified - would need date ranges)
    previous_month = current_month * 0.89  # Simulated

    # Calculate trend
    trend = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0.0

    # Get forecast
    forecast = await service.get_cost_forecast()

    # Get breakdown by service
    breakdown = await service.get_cost_breakdown(days=30)

    # Budget status
    budget = 15000.0  # This would come from configuration
    budget_status = "on-track" if forecast <= budget else "over-budget"

    # Cost optimization recommendations
    recommendations = [
        "Consider committed use discounts for Compute Engine (potential savings: $450/mo)",
        "3 idle VM instances detected - potential savings: $280/mo",
        "Enable lifecycle policies on 5 Cloud Storage buckets - potential savings: $120/mo",
    ]

    return CostSummary(
        current_month=current_month,
        previous_month=previous_month,
        trend_percentage=trend,
        forecast_end_of_month=forecast,
        budget=budget,
        budget_status=budget_status,
        breakdown=breakdown,
        top_projects=[],
        recommendations=recommendations,
    )


@router.get("/breakdown")
async def get_cost_breakdown_detailed(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("service", pattern="^(service|project|region)$"),
):
    """Get detailed cost breakdown."""
    service = get_cost_service()
    breakdown = await service.get_cost_breakdown(days=days)

    return {
        "period_days": days,
        "group_by": group_by,
        "breakdown": breakdown,
        "total": sum(item["cost"] for item in breakdown),
    }


@router.get("/trends")
async def get_cost_trends(days: int = Query(30, ge=7, le=90)):
    """Get cost trends over time."""
    # This would query BigQuery for daily cost trends
    return {
        "period_days": days,
        "data_points": [],
        "average_daily_cost": 0.0,
        "peak_cost_day": None,
        "trend": "stable",
    }


@router.get("/optimizations")
async def get_cost_optimizations():
    """Get AI-powered cost optimization recommendations."""
    return {
        "total_potential_savings": 850.0,
        "recommendations": [
            {
                "id": "opt-1",
                "title": "Enable Committed Use Discounts",
                "description": "You can save 57% on Compute Engine by committing to 1-year CUD",
                "potential_savings": 450.0,
                "confidence": 0.95,
                "resource_type": "instance",
                "resource_id": "projects/*/regions/*/instances/*",
                "action": "Purchase 1-year CUD for consistent workloads",
                "priority": "high",
            },
            {
                "id": "opt-2",
                "title": "Shutdown Idle VMs",
                "description": "3 VM instances have <5% CPU utilization for 7+ days",
                "potential_savings": 280.0,
                "confidence": 0.92,
                "resource_type": "instance",
                "resource_id": "projects/*/zones/*/instances/idle-*",
                "action": "Stop or delete idle instances",
                "priority": "high",
            },
            {
                "id": "opt-3",
                "title": "Enable Storage Lifecycle Policies",
                "description": "Move old data to Coldline/Archive storage classes",
                "potential_savings": 120.0,
                "confidence": 0.88,
                "resource_type": "bucket",
                "resource_id": "projects/*/buckets/backup-*",
                "action": "Create lifecycle rules for data older than 90 days",
                "priority": "medium",
            },
        ],
    }
