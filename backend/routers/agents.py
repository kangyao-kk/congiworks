from fastapi import APIRouter

from backend.schemas.api import AgentOut, AgentUpdate
from backend.services.agent_service import get_all_agents, get_agent, update_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents():
    return get_all_agents()


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent_by_id(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        return _not_found("Agent")
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent_by_id(agent_id: str, data: AgentUpdate):
    agent = update_agent(agent_id, data)
    if not agent:
        return _not_found("Agent")
    return agent


def _not_found(entity: str):
    from fastapi.responses import JSONResponse
    return JSONResponse({"error": f"{entity} not found"}, status_code=404)
