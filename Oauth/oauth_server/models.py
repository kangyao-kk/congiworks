import json
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from authlib.oauth2.rfc6749.util import list_to_scope, scope_to_list
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from .security import utcnow


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=128)
    password_hash: str = Field(max_length=256)
    display_name: str = Field(default="", max_length=256)
    created_at: datetime = Field(default_factory=utcnow)


class OAuthClient(SQLModel, table=True):
    __tablename__ = "oauth_clients"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    client_id: str = Field(unique=True, index=True, max_length=64)
    client_secret_hash: str = Field(max_length=256)
    client_name: str = Field(max_length=256)
    redirect_uris: str = Field(sa_column=Column(Text))  # JSON list
    grant_types: str = Field(sa_column=Column(Text))  # JSON list
    scope: str = Field(default="profile", max_length=512)
    is_confidential: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    # ------------------------------------------------------------------
    # ClientMixin implementation (Authlib protocol)
    # ------------------------------------------------------------------

    def get_client_id(self) -> str:
        return self.client_id

    def get_default_redirect_uri(self) -> str:
        uris = json.loads(self.redirect_uris)
        return uris[0] if uris else ""

    def get_allowed_scope(self, scope: str) -> str:
        if not scope:
            return ""
        allowed = set(scope_to_list(self.scope))
        return list_to_scope([s for s in scope.split() if s in allowed])

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in json.loads(self.redirect_uris)

    def check_client_secret(self, client_secret: str) -> bool:
        from .security import hash_token
        return _secrets.compare_digest(
            self.client_secret_hash, hash_token(client_secret)
        )

    def check_endpoint_auth_method(self, method: str, endpoint: str) -> bool:
        if not self.is_confidential:
            return method == "none"
        return True

    def check_response_type(self, response_type: str) -> bool:
        return response_type == "code"

    def check_grant_type(self, grant_type: str) -> bool:
        return grant_type in json.loads(self.grant_types)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_redirect_uris(self) -> list[str]:
        return json.loads(self.redirect_uris)

    def get_grant_types(self) -> list[str]:
        return json.loads(self.grant_types)

    def get_scope(self) -> str:
        return self.scope


class AuthorizationCode(SQLModel, table=True):
    __tablename__ = "authorization_codes"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    code_hash: str = Field(unique=True, index=True, max_length=128)
    client_id: str = Field(index=True, max_length=64)
    user_id: str = Field(max_length=64)
    redirect_uri: str = Field(max_length=1024)
    scope: str = Field(default="", max_length=512)
    code_challenge: Optional[str] = Field(default=None, max_length=128)
    code_challenge_method: Optional[str] = Field(default=None, max_length=16)
    expires_at: datetime = Field()
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)

    # ------------------------------------------------------------------
    # AuthorizationCodeMixin implementation (Authlib protocol)
    # ------------------------------------------------------------------

    def get_redirect_uri(self) -> str:
        return self.redirect_uri

    def get_scope(self) -> str:
        return self.scope

    def is_expired(self) -> bool:
        return utcnow() > self.expires_at


class OAuthToken(SQLModel, table=True):
    __tablename__ = "oauth_tokens"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    access_token_hash: str = Field(unique=True, index=True, max_length=128)
    refresh_token_hash: Optional[str] = Field(default=None, unique=True, max_length=128)
    client_id: str = Field(index=True, max_length=64)
    user_id: Optional[str] = Field(default=None, max_length=64)
    scope: str = Field(default="", max_length=512)
    token_type: str = Field(default="Bearer", max_length=40)
    issued_at: datetime = Field(default_factory=utcnow)
    access_token_expires_at: datetime = Field()
    refresh_token_expires_at: Optional[datetime] = Field(default=None)
    revoked_at: Optional[datetime] = Field(default=None)

    # ------------------------------------------------------------------
    # TokenMixin implementation (Authlib protocol)
    # ------------------------------------------------------------------

    def check_client(self, client) -> bool:
        return self.client_id == client.client_id

    def get_scope(self) -> str:
        return self.scope

    def get_expires_in(self) -> int:
        delta = self.access_token_expires_at - utcnow()
        return max(0, int(delta.total_seconds()))

    def is_expired(self) -> bool:
        return utcnow() > self.access_token_expires_at

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def get_user(self):
        from .database import sync_engine
        from sqlmodel import Session, select
        if not self.user_id:
            return None
        with Session(sync_engine) as session:
            return session.exec(select(User).where(User.id == self.user_id)).first()

    def get_client(self):
        from .database import sync_engine
        from sqlmodel import Session, select
        with Session(sync_engine) as session:
            return session.exec(
                select(OAuthClient).where(OAuthClient.client_id == self.client_id)
            ).first()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def is_access_token_expired(self) -> bool:
        return self.is_expired()

    def is_refresh_token_expired(self) -> bool:
        if self.refresh_token_expires_at is None:
            return False
        return utcnow() > self.refresh_token_expires_at

    def is_revoked_token(self) -> bool:
        return self.revoked_at is not None
