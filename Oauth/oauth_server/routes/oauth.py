"""OAuth 2.0 endpoints: authorize, token, revoke, userinfo."""

import asyncio
from urllib.parse import urlencode, urlparse

from authlib.oauth2.rfc6749 import OAuth2Request
from authlib.oauth2.rfc6749.requests import BasicOAuth2Payload
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings
from ..database import get_session
from ..dependencies import get_current_user
from ..models import OAuthClient, User
from ..oauth2 import server
from ..security import verify_password
from ..template_loader import templates

router = APIRouter(prefix="/oauth", tags=["oauth"])


# ---------------------------------------------------------------------------
# GET  /oauth/authorize  — entry point for authorization code flow
# ---------------------------------------------------------------------------

@router.get("/authorize")
async def authorize_get(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Authorization endpoint — requires user login, then shows consent."""
    # Validate required parameters exist before showing any UI
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    response_type = request.query_params.get("response_type")

    if not client_id or not redirect_uri or response_type != "code":
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing client_id, redirect_uri, or invalid response_type."},
            status_code=400,
        )

    client = server.query_client(client_id)
    if client is None:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client_id."},
            status_code=401,
        )

    # Validate redirect_uri against registered URIs
    if redirect_uri not in client.get_redirect_uris():
        return JSONResponse(
            {"error": "invalid_request", "error_description": "redirect_uri not registered for this client."},
            status_code=400,
        )

    # If user is not logged in, redirect to login preserving the full query string
    if user is None:
        login_url = str(request.url_for("login_page")).rstrip("/")
        full_query = str(request.url.query)
        return RedirectResponse(
            url=f"/auth/login?return_url=/oauth/authorize?{full_query}",
            status_code=status.HTTP_302_FOUND,
        )

    # Show consent page
    scope = request.query_params.get("scope", "")
    state = request.query_params.get("state", "")

    ctx = {
        "client_name": client.client_name,
        "client_id": client.client_id,
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return templates.TemplateResponse(request, "consent.html", ctx)


# ---------------------------------------------------------------------------
# POST /oauth/authorize  — user grants or denies consent
# ---------------------------------------------------------------------------

@router.post("/authorize")
async def authorize_post(
    request: Request,
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Handle consent decision — grant or deny the authorization code."""
    if user is None:
        login_url = str(request.url_for("login_page")).rstrip("/")
        full_query = str(request.url.query)
        return RedirectResponse(
            url=f"/auth/login?return_url=/oauth/authorize?{full_query}",
            status_code=status.HTTP_302_FOUND,
        )

    form = await request.form()
    action = form.get("action")  # "approve" or "deny"

    redirect_uri = form.get("redirect_uri", "")
    state = form.get("state", "")
    scope = form.get("scope", "")
    client_id = form.get("client_id", "")

    if action == "deny":
        params = urlencode({"error": "access_denied", "state": state} if state else {"error": "access_denied"})
        return RedirectResponse(url=f"{redirect_uri}?{params}", status_code=status.HTTP_302_FOUND)

    # Build an OAuth2Request and let Authlib generate the authorization code
    payload_data = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": form.get("code_challenge", ""),
        "code_challenge_method": form.get("code_challenge_method", "S256"),
    }
    oauth_request = OAuth2Request(
        method="GET",
        uri=str(request.url),
        headers=request.headers,
    )
    oauth_request._body = payload_data
    oauth_request.payload = BasicOAuth2Payload(payload_data)

    # Authlib server methods are sync — run in thread
    # Pre-fetch the grant to avoid Authlib deprecation warning
    from ..oauth2 import _UserStub
    oauth_request.user = _UserStub(user.id)
    grant = await asyncio.to_thread(server.get_consent_grant, oauth_request)
    resp = await asyncio.to_thread(
        server.create_authorization_response,
        oauth_request,
        grant_user=user,
        grant=grant,
    )

    # create_authorization_response returns (status_code, body, headers)
    status_code_val, body, headers = resp
    # headers can be dict or list of (key, value) tuples
    location = ""
    if isinstance(headers, dict):
        location = headers.get("Location", "")
    else:
        for key, value in headers:
            if key.lower() == "location":
                location = value
                break
    if location:
        return RedirectResponse(url=location, status_code=status.HTTP_302_FOUND)

    # Fallback — return the raw response body
    return JSONResponse(body, status_code=status_code_val)


# ---------------------------------------------------------------------------
# POST /oauth/token  — exchange code / refresh token / client credentials
# ---------------------------------------------------------------------------

@router.post("/token")
async def token(request: Request):
    """Token endpoint — handles all grant types."""
    body = await request.form()
    body_dict = dict(body)
    oauth_request = OAuth2Request(
        method=request.method,
        uri=str(request.url),
        headers=request.headers,
    )
    oauth_request._body = body_dict  # still needed by authenticate_client_secret_post
    oauth_request.payload = BasicOAuth2Payload(body_dict)

    resp = await asyncio.to_thread(server.create_token_response, oauth_request)
    status_code_val, body, headers = resp
    # headers can be dict or list of (key, value) tuples
    if isinstance(headers, list):
        headers = dict(headers)
    return JSONResponse(body, status_code=status_code_val, headers=headers)


# ---------------------------------------------------------------------------
# POST /oauth/revoke  — revoke a token
# ---------------------------------------------------------------------------

@router.post("/revoke")
async def revoke(request: Request):
    """Revoke an access or refresh token."""
    body = await request.form()
    token_string = body.get("token", "")

    from ..oauth2 import revoke_token
    await asyncio.to_thread(revoke_token, token_string)

    return JSONResponse({}, status_code=200)


# ---------------------------------------------------------------------------
# GET /oauth/userinfo  — OIDC-style userinfo endpoint for demo
# ---------------------------------------------------------------------------

@router.get("/userinfo")
async def userinfo(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Return info about the user associated with the Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "invalid_token"}, status_code=401)

    access_token = auth_header[7:]
    from ..oauth2 import query_token_by_access_token
    token_obj = query_token_by_access_token(access_token)
    if token_obj is None or token_obj.is_revoked() or token_obj.is_access_token_expired():
        return JSONResponse({"error": "invalid_token"}, status_code=401)

    user = None
    if token_obj.user_id:
        result = await session.exec(select(User).where(User.id == token_obj.user_id))
        user = result.first()

    if user is None:
        return JSONResponse({"error": "invalid_token"}, status_code=401)

    return JSONResponse({
        "sub": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "scope": token_obj.scope,
    })


# ---------------------------------------------------------------------------
# GET /oauth/.well-known/openid-configuration  — basic OIDC discovery
# ---------------------------------------------------------------------------

@router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request):
    issuer = settings.issuer
    return JSONResponse({
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "userinfo_endpoint": f"{issuer}/oauth/userinfo",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["profile"],
    })
