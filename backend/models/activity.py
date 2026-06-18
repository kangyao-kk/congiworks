from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


class AgentActivity(SQLModel, table=True):
    __tablename__ = "agent_activities"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    agent_id: str = Field(index=True, max_length=64)
    type: str = Field(max_length=64)
    description: str = Field(default="", max_length=1024)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
