from fastapi import APIRouter

from backend.schemas.api import ActivityIn
from backend.services.agent_service import get_agent_activities, add_agent_activity, get_agent

router = APIRouter(prefix="/api/agents", tags=["activities"])


@router.get("/{agent_id}/activities")
def list_activities(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return get_agent_activities(agent_id)


@router.post("/{agent_id}/activities")
def create_activity(agent_id: str, body: ActivityIn):
    agent = get_agent(agent_id)
    if not agent:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return add_agent_activity(agent_id, body.type, body.description)
