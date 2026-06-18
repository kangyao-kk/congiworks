"""Seed agent data from frontend/data/agents.json into the database."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models.agent import AgentConfig
from backend.schemas.api import AgentOut

AGENTS_JSON = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend/src/data/agents.json",
)


def run_seed():
    init_db()

    if not os.path.exists(AGENTS_JSON):
        print(f"  [seed] 未找到 {AGENTS_JSON}")
        return

    with open(AGENTS_JSON, "r", encoding="utf-8") as f:
        agents_data = json.load(f)

    with Session(engine) as session:
        existing_ids = set()
        for agent in session.exec(select(AgentConfig.id)).all():
            existing_ids.add(agent)

        created = 0
        updated = 0

        for a in agents_data:
            preset_json = json.dumps(a.get("presetTasks", []), ensure_ascii=False)

            if a["id"] in existing_ids:
                existing = session.get(AgentConfig, a["id"])
                existing.name = a["name"]
                existing.description = a.get("description", "")
                existing.avatar = a.get("avatar", "")
                existing.category = a.get("category", "general")
                existing.model = a.get("model", "deepseek-chat")
                existing.temperature = a.get("temperature", 0.7)
                existing.max_tokens = a.get("maxTokens", 4096)
                existing.system_prompt = a.get("systemPrompt", "")
                existing.preset_tasks = preset_json
                session.add(existing)
                updated += 1
            else:
                agent = AgentConfig(
                    id=a["id"],
                    name=a["name"],
                    description=a.get("description", ""),
                    avatar=a.get("avatar", ""),
                    category=a.get("category", "general"),
                    status="offline",
                    model=a.get("model", "deepseek-chat"),
                    temperature=a.get("temperature", 0.7),
                    max_tokens=a.get("maxTokens", 4096),
                    system_prompt=a.get("systemPrompt", ""),
                    preset_tasks=preset_json,
                    total_conversations=0,
                    avg_response_time=0.0,
                    success_rate=1.0,
                    tokens_used=0,
                )
                session.add(agent)
                created += 1

        session.commit()

    print(f"  [seed] 创建 {created} 个 Agent, 更新 {updated} 个")


if __name__ == "__main__":
    run_seed()
