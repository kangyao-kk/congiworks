from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# User-facing schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=6, max_length=256)
    display_name: str = Field(default="", max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str = ""


class ErrorResponse(BaseModel):
    error: str
    error_description: str | None = None
