import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Agent ──────────────────────────────────────────────────────────────────

class AgentOut(BaseModel):
    id: str
    name: str
    description: str = ""
    avatar: str = ""
    category: str = "general"
    status: str = "offline"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    maxTokens: int = 4096
    systemPrompt: str = ""
    presetTasks: list = []
    metrics: dict = {}
    lastActive: Optional[datetime] = None

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description,
            avatar=obj.avatar,
            category=obj.category,
            status=obj.status,
            model=obj.model,
            temperature=obj.temperature,
            maxTokens=obj.max_tokens,
            systemPrompt=obj.system_prompt,
            presetTasks=json.loads(obj.preset_tasks) if obj.preset_tasks else [],
            metrics={
                "totalConversations": obj.total_conversations,
                "avgResponseTime": obj.avg_response_time,
                "successRate": obj.success_rate,
                "tokensUsed": obj.tokens_used,
            },
            lastActive=obj.last_active,
        )


class AgentUpdate(BaseModel):
    model_config = {"populate_by_name": True}

    status: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = Field(None, alias="maxTokens")
    system_prompt: Optional[str] = Field(None, alias="systemPrompt")


# ── Message ────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    thinking: Optional[list[dict]] = None


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1)


# ── Activity ───────────────────────────────────────────────────────────────

class ActivityOut(BaseModel):
    id: str
    type: str
    description: str
    timestamp: datetime


class ActivityIn(BaseModel):
    type: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=1024)


# ── Knowledge Base ─────────────────────────────────────────────────────────

class KnowledgeFileOut(BaseModel):
    id: str
    name: str
    size: int
    status: str
    chunks: int
    uploadDate: datetime
    fakeUrl: str = ""


# ── User ───────────────────────────────────────────────────────────────────

class UserProfileOut(BaseModel):
    id: str
    name: str
    email: str
    avatar: str
    role: str
