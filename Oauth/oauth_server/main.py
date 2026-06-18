"""FastAPI application factory and CLI helpers."""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import init_db, sync_engine
from .models import OAuthClient
from .security import hash_password, hash_token, generate_token
from .routes.auth import router as auth_router
from .routes.oauth import router as oauth_router


# ---------------------------------------------------------------------------
# Lifespan — create tables on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OAuth 2.0 Authorization Server",
    description="OAuth 2.0 认证服务器 — built with FastAPI + Authlib + SQLModel",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie=settings.session_cookie_name)

app.include_router(auth_router)
app.include_router(oauth_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login")
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head><meta charset="utf-8"><title>OAuth Server</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="bg-white rounded-2xl shadow-md p-8 text-center">
        <h1 class="text-2xl font-bold text-gray-800 mb-2">OAuth 2.0 认证服务器</h1>
        <p class="text-gray-500 mb-4">运行中</p>
        <p class="text-sm text-gray-400 mb-4">已登录用户: {user_id}</p>
        <div class="space-x-3">
            <a href="/docs" class="text-indigo-600 hover:underline text-sm">API 文档</a>
            <a href="/auth/logout" class="text-red-500 hover:underline text-sm">退出登录</a>
            <a href="/oauth/.well-known/openid-configuration" class="text-indigo-600 hover:underline text-sm">OIDC 发现</a>
        </div>
    </div></body></html>
    """)


# ---------------------------------------------------------------------------
# CLI: create a test OAuth client
# ---------------------------------------------------------------------------
def create_test_client(
    client_name: str = "Test Client",
    redirect_uris: str = "http://localhost:9000/callback",
    scope: str = "profile",
):
    """Create a test OAuth client in the database (synchronous, for CLI use)."""
    from sqlmodel import Session

    client_id = generate_token(32)
    client_secret = generate_token(48)

    with Session(sync_engine) as session:
        client = OAuthClient(
            client_id=client_id,
            client_secret_hash=hash_token(client_secret),
            client_name=client_name,
            redirect_uris=json.dumps(redirect_uris.split(",")),
            grant_types=json.dumps(["authorization_code", "client_credentials", "refresh_token"]),
            scope=scope,
            is_confidential=True,
        )
        session.add(client)
        session.commit()

    print(f"\n  Test client created:\n")
    print(f"  client_id     = {client_id}")
    print(f"  client_secret = {client_secret}")
    print(f"  redirect_uris = {redirect_uris}")
    print(f"  scope         = {scope}\n")
    return client_id, client_secret
