"""
OAuth 2.0 Provider — built on Authlib's AuthorizationServer.

Subclasses AuthorizationServer and overrides the required abstract methods.
Uses a *sync* SQLAlchemy session internally because Authlib's grant classes
are synchronous. FastAPI route handlers wrap calls via ``asyncio.to_thread``.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from authlib.oauth2.rfc6749 import AuthorizationServer as _AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc7636 import CodeChallenge
from sqlmodel import Session, select

from .config import settings
from .database import sync_engine
from .models import AuthorizationCode, OAuthClient, OAuthToken
from .security import generate_token, hash_token, utcnow


# ---------------------------------------------------------------------------
# Authlib grant implementations
# ---------------------------------------------------------------------------

class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Authorization Code grant with PKCE support."""

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_post", "client_secret_basic"]

    def save_authorization_code(self, code: str, request):
        code_challenge = request.payload.data.get("code_challenge")
        code_challenge_method = request.payload.data.get("code_challenge_method")

        with Session(sync_engine) as session:
            auth_code = AuthorizationCode(
                code_hash=hash_token(code),
                client_id=request.client.client_id,
                user_id=request.user.id if request.user else "",
                redirect_uri=request.payload.redirect_uri,
                scope=request.scope or "",
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                expires_at=utcnow() + timedelta(minutes=settings.authorization_code_expires_minutes),
            )
            session.add(auth_code)
            session.commit()

    def query_authorization_code(self, code: str, client=None):
        code_h = hash_token(code)
        with Session(sync_engine) as session:
            return session.exec(
                select(AuthorizationCode).where(AuthorizationCode.code_hash == code_h)
            ).first()

    def delete_authorization_code(self, code, client=None):
        with Session(sync_engine) as session:
            # Authlib may pass the code string or the AuthorizationCode object
            if isinstance(code, str):
                code_h = hash_token(code)
                auth_code = session.exec(
                    select(AuthorizationCode).where(AuthorizationCode.code_hash == code_h)
                ).first()
            else:
                # Already an AuthorizationCode object — attach it to this session
                auth_code = session.merge(code)
            if auth_code:
                auth_code.used = True
                session.add(auth_code)
                session.commit()

    def authenticate_user(self, authorization_code):
        return _UserStub(authorization_code.user_id)


class ClientCredentialsGrant(grants.ClientCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_post", "client_secret_basic"]


class RefreshTokenGrant(grants.RefreshTokenGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_post", "client_secret_basic"]

    def authenticate_refresh_token(self, refresh_token: str):
        rt_hash = hash_token(refresh_token)
        with Session(sync_engine) as session:
            token = session.exec(
                select(OAuthToken).where(OAuthToken.refresh_token_hash == rt_hash)
            ).first()
            if token and not token.is_revoked() and not token.is_refresh_token_expired():
                return token
        return None

    def authenticate_user(self, credential):
        return _UserStub(credential.user_id) if credential.user_id else None

    def revoke_old_credential(self, credential):
        """Revoke the old refresh token — credential is the OAuthToken object."""
        with Session(sync_engine) as session:
            cred = session.merge(credential)
            cred.revoked_at = utcnow()
            session.add(cred)
            session.commit()


class _UserStub:
    """Minimal user object Authlib expects on ``request.user``."""
    def __init__(self, user_id: str):
        self.id = user_id


# ---------------------------------------------------------------------------
# AuthorizationServer subclass
# ---------------------------------------------------------------------------

class AgencyAuthorizationServer(_AuthorizationServer):
    """Custom AuthorizationServer with database-backed client & token storage."""

    def query_client(self, client_id: str) -> Optional[OAuthClient]:
        with Session(sync_engine) as session:
            return session.exec(
                select(OAuthClient).where(OAuthClient.client_id == client_id)
            ).first()

    def save_token(self, token_data: dict, request):
        with Session(sync_engine) as session:
            token = OAuthToken(
                access_token_hash=hash_token(token_data["access_token"]),
                refresh_token_hash=hash_token(token_data.get("refresh_token")) if token_data.get(
                    "refresh_token") else None,
                client_id=request.client.client_id,
                user_id=request.user.id if request.user else None,
                scope=token_data.get("scope", ""),
                token_type=token_data.get("token_type", "Bearer"),
                access_token_expires_at=utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
                refresh_token_expires_at=utcnow() + timedelta(days=settings.refresh_token_expires_days)
                if token_data.get("refresh_token") else None,
            )
            session.add(token)
            session.commit()

    def create_oauth2_request(self, request):
        """Accept pre-built OAuth2Request objects from FastAPI routes."""
        return request

    def handle_response(self, status, body, headers):
        """Return raw (status, body, headers) tuple for FastAPI to consume."""
        return status, body, headers

    def send_signal(self, name, *args, **kwargs):
        """Signals are not needed for this implementation."""
        pass


# ---------------------------------------------------------------------------
# Token generator
# ---------------------------------------------------------------------------

def _token_generator(
    grant_type: str,
    client,
    user=None,
    scope=None,
    expires_in=None,
    include_refresh_token=True,
):
    access_token = generate_token(48)
    token: dict = {
        "token_type": "Bearer",
        "access_token": access_token,
        "expires_in": expires_in or (settings.access_token_expires_minutes * 60),
        "scope": scope or "",
    }
    if include_refresh_token:
        token["refresh_token"] = generate_token(48)
    return token


# ---------------------------------------------------------------------------
# Build the server instance
# ---------------------------------------------------------------------------

server = AgencyAuthorizationServer(scopes_supported=["profile"])

# Register token generator
server.register_token_generator("default", _token_generator)

# Register grants
server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True)])
server.register_grant(ClientCredentialsGrant)
server.register_grant(RefreshTokenGrant)


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------------------

def query_token_by_access_token(token_string: str) -> Optional[OAuthToken]:
    t_hash = hash_token(token_string)
    with Session(sync_engine) as session:
        return session.exec(
            select(OAuthToken).where(OAuthToken.access_token_hash == t_hash)
        ).first()


def revoke_token(token_string: str):
    t_hash = hash_token(token_string)
    with Session(sync_engine) as session:
        token = session.exec(
            select(OAuthToken).where(
                (OAuthToken.access_token_hash == t_hash)
                | (OAuthToken.refresh_token_hash == t_hash)
            )
        ).first()
        if token:
            token.revoked_at = utcnow()
            session.add(token)
            session.commit()
