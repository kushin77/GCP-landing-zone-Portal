from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    user: str

@router.get("/login")
async def login(user: str):
    """Dummy login for tests."""
    return {"status": "success", "user": user}

@router.post("/login")
async def login_post(request: LoginRequest):
    """Dummy login POST for tests."""
    return {"status": "success", "user": request.user}
