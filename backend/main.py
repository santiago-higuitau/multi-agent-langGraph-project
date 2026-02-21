"""
AI Dev Team - Main FastAPI Application

Multi-agent system for intelligent software delivery.
"""

from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

app = FastAPI(
    title="AI Dev Team",
    description="Multi-agent system that transforms a brief into a fully functional intelligent application",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "AI Dev Team",
        "version": "0.1.0",
        "description": "Multi-agent software delivery system",
        "docs": "/docs",
        "endpoints": {
            "start_run": "POST /api/runs",
            "get_run": "GET /api/runs/{run_id}",
            "list_runs": "GET /api/runs",
            "get_artifacts": "GET /api/runs/{run_id}/artifacts",
            "get_decisions": "GET /api/runs/{run_id}/decisions",
            "hitl_decision": "POST /api/runs/{run_id}/hitl",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
