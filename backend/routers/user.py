from fastapi import APIRouter

from backend.schemas.api import UserProfileOut

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", response_model=UserProfileOut)
def get_profile():
    return UserProfileOut(
        id="user-001",
        name="管理员",
        email="admin@agency.local",
        avatar="https://api.dicebear.com/9.x/avataaars/svg?seed=admin",
        role="admin",
    )
