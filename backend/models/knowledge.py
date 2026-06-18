from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class KnowledgeFile(SQLModel, table=True):
    __tablename__ = "kb_files"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    name: str = Field(max_length=512)
    size: int = Field(default=0)
    status: str = Field(default="processing", max_length=32)
    chunks: int = Field(default=0)
    source_path: str = Field(default="", max_length=1024)
    content: str = Field(default="", sa_column=Column(Text))
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
