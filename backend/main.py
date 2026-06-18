import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import agents, conversations, activities, knowledge, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Agency Backend API",
    description="Agency 代运营 Agent 控制面板后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(activities.router)
app.include_router(knowledge.router)
app.include_router(user.router)


if __name__ == "__main__":
    import uvicorn
    from backend.config import config
    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.APP_PORT, reload=True)
