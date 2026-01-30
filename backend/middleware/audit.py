import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("backend.middleware.audit")

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging of sensitive operations.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log metadata for audit
        # In a real system, this would go to BigQuery or Cloud Logging
        audit_entry = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency": duration,
            "client_ip": request.client.host if request.client else "unknown",
            "user": getattr(request.state, "user", "anonymous")
        }
        
        # Only log successful modifications or all API calls depending on policy
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            logger.info(f"AUDIT LOG: {audit_entry}")
            
        return response
