import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from backend.database import engine
from backend.models.agent import AgentConfig
from backend.models.activity import AgentActivity
from backend.models.conversation import ConversationMessage
from backend.schemas.api import AgentOut, AgentUpdate


def get_all_agents() -> list[AgentOut]:
    with Session(engine) as session:
        agents = session.exec(select(AgentConfig).order_by(AgentConfig.created_at)).all()
        return [AgentOut.from_orm(a) for a in agents]


def get_agent(agent_id: str) -> AgentOut | None:
    with Session(engine) as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            return None
        return AgentOut.from_orm(agent)


def update_agent(agent_id: str, data: AgentUpdate) -> AgentOut | None:
    with Session(engine) as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            return None

        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(agent, key, value)
        agent.last_active = datetime.now(timezone.utc)
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return AgentOut.from_orm(agent)


def get_agent_activities(agent_id: str, limit: int = 50) -> list[dict]:
    with Session(engine) as session:
        activities = session.exec(
            select(AgentActivity)
            .where(AgentActivity.agent_id == agent_id)
            .order_by(AgentActivity.timestamp.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": a.id,
                "type": a.type,
                "description": a.description,
                "timestamp": a.timestamp,
            }
            for a in activities
        ]


def add_agent_activity(agent_id: str, activity_type: str, description: str = "") -> dict:
    with Session(engine) as session:
        act = AgentActivity(
            agent_id=agent_id,
            type=activity_type,
            description=description,
        )
        session.add(act)
        session.commit()
        session.refresh(act)
        return {
            "id": act.id,
            "type": act.type,
            "description": act.description,
            "timestamp": act.timestamp,
        }


def update_agent_metrics(agent_id: str, total_tokens: int, response_time: float, success: bool):
    with Session(engine) as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            return
        agent.total_conversations += 1
        agent.tokens_used += total_tokens
        n = max(agent.total_conversations, 1)
        agent.avg_response_time = (agent.avg_response_time * (n - 1) + response_time) / n
        if not success:
            agent.success_rate = (agent.success_rate * (n - 1)) / n
        agent.last_active = datetime.now(timezone.utc)
        session.add(agent)
        session.commit()


# ── Conversation Messages ──────────────────────────────────────────────────

def get_conversation_messages(agent_id: str) -> list[dict]:
    with Session(engine) as session:
        msgs = session.exec(
            select(ConversationMessage)
            .where(ConversationMessage.agent_id == agent_id)
            .order_by(ConversationMessage.timestamp)
        ).all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "thinking": json.loads(m.thinking) if m.thinking and m.thinking != "[]" else None,
            }
            for m in msgs
        ]


def save_conversation_message(agent_id: str, role: str, content: str, thinking: list | None = None) -> dict:
    with Session(engine) as session:
        msg = ConversationMessage(
            agent_id=agent_id,
            role=role,
            content=content,
            thinking=json.dumps(thinking or [], ensure_ascii=False),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "thinking": thinking,
        }


def delete_conversation_messages(agent_id: str) -> int:
    with Session(engine) as session:
        result = session.exec(
            select(ConversationMessage).where(ConversationMessage.agent_id == agent_id)
        ).all()
        count = len(result)
        for m in result:
            session.delete(m)
        session.commit()
        return count
