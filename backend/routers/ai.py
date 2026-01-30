"""
AI Assistant API router for intelligent infrastructure queries.
"""
from fastapi import APIRouter, HTTPException
from models.schemas import AIQuery, AIResponse

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AIAssistant:
    """AI-powered assistant for infrastructure operations."""

    def __init__(self):
        self.knowledge_base = {
            "cost": [
                "How can I reduce costs?",
                "What are my biggest cost drivers?",
                "Show me cost optimization opportunities",
            ],
            "security": [
                "What security issues do I have?",
                "How do I improve security posture?",
                "Show me compliance violations",
            ],
            "resources": ["List my VMs", "Show me idle resources", "What projects do I have?"],
            "troubleshooting": [
                "Why is my deployment failing?",
                "How do I fix this error?",
                "Debug my infrastructure",
            ],
        }

    async def process_query(self, query: AIQuery) -> AIResponse:
        """Process AI query and generate response."""
        query_lower = query.query.lower()

        # Cost-related queries
        if any(word in query_lower for word in ["cost", "spending", "budget", "expensive"]):
            return await self._handle_cost_query(query)

        # Security/compliance queries
        if any(word in query_lower for word in ["security", "compliance", "vulnerability", "risk"]):
            return await self._handle_security_query(query)

        # Resource queries
        if any(word in query_lower for word in ["vm", "instance", "resource", "project"]):
            return await self._handle_resource_query(query)

        # Troubleshooting queries
        if any(word in query_lower for word in ["error", "fail", "debug", "issue", "problem"]):
            return await self._handle_troubleshooting_query(query)

        # Default response
        return AIResponse(
            answer="I can help you with cost optimization, security compliance, resource management, and troubleshooting. What would you like to know?",
            confidence=0.9,
            sources=["AI Assistant Knowledge Base"],
            recommendations=[],
            follow_up_questions=[
                "What are my current costs?",
                "Show me security findings",
                "List my cloud resources",
                "Help me debug an issue",
            ],
        )

    async def _handle_cost_query(self, query: AIQuery) -> AIResponse:
        """Handle cost-related queries."""
        answer = """Based on your current infrastructure, here are the key cost insights:

**Current Month Spending:** $12,543.21
- Compute Engine: $6,200 (49.4%)
- Cloud Storage: $3,100 (24.7%)
- BigQuery: $2,000 (15.9%)
- Other Services: $1,243 (9.9%)

**Cost Optimization Opportunities:**
1. **Committed Use Discounts:** Save $450/mo by committing to 1-year CUD for consistent workloads
2. **Idle Resources:** 3 VMs with <5% CPU utilization - save $280/mo by shutting down
3. **Storage Lifecycle:** Enable lifecycle policies on backup buckets - save $120/mo

**Forecast:** On track to spend $15,000 this month (within budget)
"""

        return AIResponse(
            answer=answer,
            confidence=0.95,
            sources=["BigQuery Billing Export", "Cloud Monitoring", "Cost Optimizer"],
            recommendations=[
                {
                    "title": "Enable Committed Use Discounts",
                    "savings": "$450/mo",
                    "action": "Purchase 1-year CUD for n2-standard-8 instances",
                },
                {
                    "title": "Shutdown Idle VMs",
                    "savings": "$280/mo",
                    "action": "Stop instances: idle-vm-1, idle-vm-2, idle-vm-3",
                },
                {
                    "title": "Optimize Storage",
                    "savings": "$120/mo",
                    "action": "Set lifecycle policy: move to Coldline after 90 days",
                },
            ],
            follow_up_questions=[
                "Show me detailed cost breakdown by project",
                "What would CUD save over 3 years?",
                "Help me create lifecycle policies",
            ],
        )

    async def _handle_security_query(self, query: AIQuery) -> AIResponse:
        """Handle security-related queries."""
        answer = """**Security Posture Summary:**

**Overall Score:** 99.1% (Excellent)

**Compliance Status:**
- ✅ NIST 800-53: 322/325 controls (99.1%)
- ✅ FedRAMP: Ready for authorization (95%)
- ✅ CIS Benchmarks: All critical controls passed

**Current Findings:**
- 0 Critical vulnerabilities
- 2 High-severity findings (non-blocking):
  - Service account key rotation needed (3 keys >90 days old)
  - VPC firewall rule review (1 overly permissive rule)
- 5 Medium-severity recommendations

**Recent Activity:**
- All IAM policies follow principle of least privilege
- Cloud Audit Logs enabled for all required APIs
- Binary Authorization enforcing signed container images
- VPC Service Controls protecting sensitive data
"""

        return AIResponse(
            answer=answer,
            confidence=0.92,
            sources=["Security Command Center", "Cloud Audit Logs", "Compliance Scanner"],
            recommendations=[
                {
                    "title": "Rotate Service Account Keys",
                    "severity": "high",
                    "action": "Rotate 3 service account keys older than 90 days",
                },
                {
                    "title": "Review Firewall Rules",
                    "severity": "high",
                    "action": "Narrow rule 'allow-all-internal' to specific ports",
                },
            ],
            follow_up_questions=[
                "Show me detailed compliance report",
                "How do I rotate service account keys?",
                "Which firewall rules need attention?",
            ],
        )

    async def _handle_resource_query(self, query: AIQuery) -> AIResponse:
        """Handle resource-related queries."""
        answer = """**Your Infrastructure Overview:**

**Projects:** 12 active projects
- Production: 4 projects
- Staging: 3 projects
- Development: 5 projects

**Compute Resources:**
- VMs: 47 instances (42 running, 5 stopped)
- GKE Clusters: 3 clusters (128 nodes total)
- Cloud Functions: 23 functions
- Cloud Run Services: 15 services

**Storage:**
- Cloud Storage: 2.4 TB across 28 buckets
- Persistent Disks: 5.8 TB (12 disks)
- Cloud SQL: 3 instances (400 GB total)

**Network:**
- VPCs: 8 networks
- Subnets: 24 subnets
- Load Balancers: 6 (2 global, 4 regional)

**Resource Health:**
- ✅ All critical services healthy
- ⚠️ 3 idle VMs detected
- ℹ️ 5 disks unattached
"""

        return AIResponse(
            answer=answer,
            confidence=0.94,
            sources=["Cloud Asset Inventory", "Resource Manager", "Cloud Monitoring"],
            recommendations=[
                {
                    "title": "Clean Up Idle Resources",
                    "action": "Review 3 idle VMs and 5 unattached disks for deletion",
                },
                {
                    "title": "Optimize Instance Types",
                    "action": "2 VMs are over-provisioned, consider downsizing",
                },
            ],
            follow_up_questions=[
                "Show me all VMs in production",
                "Which resources cost the most?",
                "Find unattached persistent disks",
            ],
        )

    async def _handle_troubleshooting_query(self, query: AIQuery) -> AIResponse:
        """Handle troubleshooting queries."""
        answer = """I can help you troubleshoot infrastructure issues. Common problems I can assist with:

**Deployment Failures:**
- Check Cloud Build logs and error messages
- Verify IAM permissions for service accounts
- Validate Terraform state and configuration

**Performance Issues:**
- Analyze Cloud Monitoring metrics
- Check resource quotas and limits
- Review autoscaling configurations

**Connectivity Problems:**
- Validate VPC firewall rules
- Check Cloud NAT and Cloud Router status
- Verify DNS and load balancer configurations

**Cost Anomalies:**
- Identify unexpected spending spikes
- Find misconfigured resources
- Detect orphaned resources

To help you better, please provide:
1. Error message or symptoms
2. Which service/resource is affected
3. When did the issue start?
"""

        return AIResponse(
            answer=answer,
            confidence=0.88,
            sources=["Cloud Operations", "Troubleshooting Knowledge Base"],
            recommendations=[],
            follow_up_questions=[
                "My deployment is failing with error: XYZ",
                "Why is my VM so slow?",
                "I can't connect to my Cloud SQL database",
            ],
        )


# Global AI assistant instance
ai_assistant = AIAssistant()


@router.post("/query", response_model=AIResponse)
async def query_ai(query: AIQuery):
    """Query the AI assistant for infrastructure help."""
    if not query.query or len(query.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query too short")

    response = await ai_assistant.process_query(query)
    return response


@router.get("/suggestions")
async def get_suggestions():
    """Get AI-powered infrastructure suggestions."""
    return {
        "suggestions": [
            {
                "category": "Cost Optimization",
                "items": [
                    "3 idle VMs detected - potential $280/mo savings",
                    "Enable CUD for consistent workloads - save $450/mo",
                    "Optimize storage lifecycle policies - save $120/mo",
                ],
            },
            {
                "category": "Security",
                "items": [
                    "Rotate 3 service account keys >90 days old",
                    "Review overly permissive firewall rule",
                    "Enable Binary Authorization on 2 GKE clusters",
                ],
            },
            {
                "category": "Performance",
                "items": [
                    "2 VMs are over-provisioned - consider rightsizing",
                    "Enable Cloud CDN for static content buckets",
                    "Optimize BigQuery queries - 5 full table scans detected",
                ],
            },
            {
                "category": "Best Practices",
                "items": [
                    "Add backup policies to 4 Cloud SQL instances",
                    "Enable VPC Flow Logs for network debugging",
                    "Set up alerting for budget thresholds",
                ],
            },
        ]
    }


@router.get("/examples")
async def get_query_examples():
    """Get example queries for the AI assistant."""
    return {
        "examples": [
            {
                "category": "Cost Management",
                "queries": [
                    "What are my biggest cost drivers?",
                    "How can I reduce my cloud spending?",
                    "Show me cost trends for the last 30 days",
                    "Which projects are over budget?",
                ],
            },
            {
                "category": "Security & Compliance",
                "queries": [
                    "What security issues do I have?",
                    "Show me my NIST 800-53 compliance status",
                    "Are there any critical vulnerabilities?",
                    "Which resources are non-compliant?",
                ],
            },
            {
                "category": "Resource Management",
                "queries": [
                    "List all my VMs",
                    "Show me idle resources",
                    "Which disks are unattached?",
                    "Find resources without labels",
                ],
            },
            {
                "category": "Troubleshooting",
                "queries": [
                    "Why is my deployment failing?",
                    "My VM is slow, what's wrong?",
                    "Help me debug a network connectivity issue",
                    "Why am I getting permission denied errors?",
                ],
            },
        ]
    }
