from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_messages"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    agent_id: str = Field(index=True, max_length=64)
    role: str = Field(max_length=32)
    content: str = Field(sa_column=Column(Text))
    thinking: str = Field(default="[]", sa_column=Column(Text))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
