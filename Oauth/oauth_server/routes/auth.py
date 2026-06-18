"""User-facing authentication routes: login, register, logout."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..database import get_session
from ..models import User
from ..security import hash_password, verify_password
from ..template_loader import templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    return_url = request.query_params.get("return_url", "/")
    return templates.TemplateResponse(request, "login.html", {"return_url": return_url, "error": ""})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    return_url: str = Form("/"),
    session: AsyncSession = Depends(get_session),
):
    """Process login form submission."""
    result = await session.exec(select(User).where(User.username == username))
    user = result.first()

    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html",
            {"return_url": return_url, "error": "用户名或密码错误"},
            status_code=401,
        )

    request.session["user_id"] = user.id
    safe_url = return_url if return_url.startswith("/") else "/"
    return RedirectResponse(url=safe_url, status_code=status.HTTP_302_FOUND)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render the registration page."""
    return templates.TemplateResponse(request, "register.html", {"error": ""})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(..., min_length=1, max_length=128),
    password: str = Form(..., min_length=6, max_length=256),
    display_name: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    """Process registration form."""
    existing = await session.exec(select(User).where(User.username == username))
    if existing.first():
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "用户名已被占用"},
            status_code=409,
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    session.add(user)
    await session.commit()

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
