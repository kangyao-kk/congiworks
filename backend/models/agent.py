from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class AgentConfig(SQLModel, table=True):
    __tablename__ = "agent_configs"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    name: str = Field(max_length=256)
    description: str = Field(default="", max_length=1024)
    avatar: str = Field(default="", max_length=1024)
    category: str = Field(default="general", max_length=64)
    status: str = Field(default="offline", max_length=32)
    model: str = Field(default="deepseek-chat", max_length=128)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4096)
    system_prompt: str = Field(default="", max_length=4096)
    preset_tasks: str = Field(default="[]", max_length=4096)
    total_conversations: int = Field(default=0)
    avg_response_time: float = Field(default=0.0)
    success_rate: float = Field(default=1.0)
    tokens_used: int = Field(default=0)
    last_active: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
