"""FastAPI dependency injection helpers."""

from typing import Optional

from fastapi import Cookie, Depends, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .database import get_session
from .models import User


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Return the currently logged-in user, or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    result = await session.exec(select(User).where(User.id == user_id))
    return result.first()
