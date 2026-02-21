"""
AI Dev Team - API Routes

REST endpoints for the control web interface.

Key design decisions:
- Pipeline execution runs in background (asyncio.create_task) so API never blocks
- HITL status is derived from LangGraph's interrupt state (current_state.next),
  NOT from the state values — because interrupt_before means the gate node
  never actually executes until resumed
- Double-submit on HITL is handled gracefully (returns 200, not 400)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import asyncio

from ..graph.state import create_initial_state
from ..graph.workflow import compile_workflow

router = APIRouter(prefix="/api", tags=["pipeline"])

# In-memory storage
runs_store: dict = {}
workflow_app = None
# Track which runs have a background task running
_running_tasks: dict[str, asyncio.Task] = {}


def get_workflow():
    global workflow_app
    if workflow_app is None:
        workflow_app = compile_workflow()
    return workflow_app


def _derive_run_status(run_id: str, state_values: dict, next_nodes: tuple) -> dict:
    """
    Derive the real status/phase from LangGraph's interrupt state.
    
    Because we use interrupt_before on HITL gates, the gate node never runs,
    so state.status stays 'running'. We detect the interrupt by checking next_nodes.
    """
    status = state_values.get("status", "unknown")
    current_phase = state_values.get("current_phase", "unknown")
    current_agent = state_values.get("current_agent", "")

    # If pipeline is interrupted before a HITL gate, override status
    # BUT if there's an active background task, the gate was already approved
    # and the pipeline just hasn't advanced past it yet — report "running"
    has_active_task = run_id in _running_tasks and not _running_tasks[run_id].done()

    if "hitl_gate_1" in next_nodes:
        if has_active_task:
            status = "running"
            current_phase = "building"
            current_agent = "hitl_gate_1"
        else:
            status = "waiting_hitl"
            current_phase = "hitl_gate_1"
            current_agent = "hitl_gate_1"
    elif "hitl_gate_2" in next_nodes:
        if has_active_task:
            status = "running"
            current_phase = "devops"
            current_agent = "hitl_gate_2"
        else:
            status = "waiting_hitl"
            current_phase = "hitl_gate_2"
            current_agent = "hitl_gate_2"
    elif not next_nodes and status == "running":
        # No next nodes = pipeline finished
        status = "completed"
        current_phase = "done"
        current_agent = ""
    elif has_active_task:
        # Background task still running
        status = "running"

    return {
        "status": status,
        "current_phase": current_phase,
        "current_agent": current_agent,
    }


async def _run_pipeline_background(run_id: str, initial_state=None):
    """
    Execute the LangGraph pipeline in background.
    Runs until the next interrupt (HITL gate) or END.
    """
    app = get_workflow()
    config = runs_store[run_id]["config"]

    try:
        stream_input = initial_state
        async for event in app.astream(stream_input, config=config):
            for node_name, _ in event.items():
                print(f"  ✓ Node completed: {node_name}")

        # Update stored state
        current_state = app.get_state(config)
        runs_store[run_id]["state"] = current_state

        # Check if we reached end
        if not current_state.next:
            print(f"\n✅ Run {run_id} completed!")
        else:
            print(f"\n⏸️  Run {run_id} paused at: {current_state.next}")

    except Exception as e:
        print(f"\n❌ Run {run_id} error: {type(e).__name__}: {e}")
        # Try to update state with error
        try:
            app.update_state(config, {
                "status": "error",
                "errors": [{"error": str(e), "type": type(e).__name__}],
            })
        except Exception:
            pass
    finally:
        # Clean up task reference
        _running_tasks.pop(run_id, None)


# --- Agent Registry & Graph Info ---

@router.get("/agents")
async def get_agent_registry():
    """Get the registry of all agents with their roles and descriptions."""
    from ..graph.nodes import AGENT_REGISTRY
    return {
        "agents": AGENT_REGISTRY,
        "total": len(AGENT_REGISTRY),
        "phases": {
            "planning": [k for k, v in AGENT_REGISTRY.items() if v["phase"] == "planning"],
            "building": [k for k, v in AGENT_REGISTRY.items() if v["phase"] == "building"],
            "qa": [k for k, v in AGENT_REGISTRY.items() if v["phase"] == "qa"],
            "integration": [k for k, v in AGENT_REGISTRY.items() if v["phase"] == "integration"],
            "devops": [k for k, v in AGENT_REGISTRY.items() if v["phase"] == "devops"],
        },
    }


@router.get("/graph")
async def get_graph_info():
    """Get the workflow graph structure."""
    app = get_workflow()
    graph = app.get_graph()
    nodes = list(graph.nodes.keys())
    return {
        "nodes": nodes,
        "total_nodes": len(nodes),
        "pattern": "Subagents with fan-out parallelization",
        "parallel_groups": {"builders": ["backend_builder", "frontend_builder"]},
        "hitl_gates": ["hitl_gate_1", "hitl_gate_2"],
    }


# --- Request/Response Models ---

class StartRunRequest(BaseModel):
    brief: str


class HITLDecision(BaseModel):
    decision: str  # approved | rejected | changes_requested
    feedback: Optional[str] = ""


# --- Endpoints ---

@router.post("/runs", response_model=dict)
async def start_run(request: StartRunRequest):
    """
    Start a new pipeline run with a brief.
    
    Launches the pipeline in background and returns immediately.
    The frontend polls GET /runs/{id} to track progress.
    """
    run_id = str(uuid.uuid4())[:8]

    initial_state = create_initial_state(run_id=run_id, brief=request.brief)
    config = {"configurable": {"thread_id": run_id}}

    # Store run before launching
    runs_store[run_id] = {
        "config": config,
        "state": None,
    }

    print(f"\n🚀 Starting run {run_id}")
    print(f"📄 Brief: {request.brief[:100]}...")
    print(f"{'='*60}\n")

    # Launch pipeline in background — returns immediately
    task = asyncio.create_task(_run_pipeline_background(run_id, initial_state))
    _running_tasks[run_id] = task

    return {
        "run_id": run_id,
        "status": "running",
        "current_phase": "planning",
        "current_agent": "BA Agent",
        "message": "Pipeline started. Polling for updates...",
    }


@router.get("/runs/{run_id}", response_model=dict)
async def get_run(run_id: str):
    """Get the current state of a run."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    current_state = app.get_state(config)
    state_values = current_state.values

    # Derive real status from interrupt state
    derived = _derive_run_status(run_id, state_values, current_state.next)

    return {
        "run_id": run_id,
        "status": derived["status"],
        "current_phase": derived["current_phase"],
        "current_agent": derived["current_agent"],
        "planning_iteration": state_values.get("planning_iteration", 0),
        "num_requirements": len(state_values.get("requirements", [])),
        "num_user_stories": len(state_values.get("user_stories", [])),
        "num_test_cases": len(state_values.get("test_cases", [])),
        "num_generated_files": len(state_values.get("generated_files", [])),
        "deployment_ready": state_values.get("deployment_ready", False),
        "brief": state_values.get("brief", ""),
        "next_steps": current_state.next,
        "next_agent": state_values.get("next_agent", ""),
    }


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(run_id: str):
    """Get all artifacts generated by the pipeline."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    return {
        "requirements": state_values.get("requirements", []),
        "inception": state_values.get("inception"),
        "user_stories": state_values.get("user_stories", []),
        "tech_spec": state_values.get("tech_spec"),
        "backend_spec": state_values.get("backend_spec"),
        "frontend_spec": state_values.get("frontend_spec"),
        "qa_spec": state_values.get("qa_spec"),
        "devops_spec": state_values.get("devops_spec"),
        "test_cases": state_values.get("test_cases", []),
        "integration_score": state_values.get("integration_score", 0),
        "integration_issues": state_values.get("integration_issues", []),
        "generated_files": [
            {"path": f["path"], "us_ids": f["us_ids"], "created_by": f["created_by"]}
            for f in state_values.get("generated_files", [])
        ],
        "er_diagram_svg": state_values.get("er_diagram_svg", ""),
        "sequence_diagrams_svg": state_values.get("sequence_diagrams_svg", []),
    }


@router.get("/runs/{run_id}/files")
async def get_generated_files(run_id: str):
    """Get all generated files WITH their content."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    all_files = (
        state_values.get("generated_files", []) +
        state_values.get("docker_files", [])
    )

    return {
        "files": [
            {
                "path": f["path"],
                "content": f["content"],
                "us_ids": f["us_ids"],
                "created_by": f["created_by"],
                "lines": f["content"].count("\n") + 1,
            }
            for f in all_files
        ],
        "total": len(all_files),
    }


@router.get("/runs/{run_id}/files/{file_path:path}")
async def get_file_content(run_id: str, file_path: str):
    """Get the content of a specific generated file."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    all_files = (
        state_values.get("generated_files", []) +
        state_values.get("docker_files", [])
    )

    for f in all_files:
        if f["path"] == file_path:
            return {
                "path": f["path"],
                "content": f["content"],
                "us_ids": f["us_ids"],
                "created_by": f["created_by"],
                "lines": f["content"].count("\n") + 1,
            }

    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


@router.get("/runs/{run_id}/decisions")
async def get_decisions_log(run_id: str):
    """Get the decision log for a run."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    return {
        "decisions": state_values.get("decisions_log", []),
        "total": len(state_values.get("decisions_log", [])),
    }


@router.get("/runs/{run_id}/activity")
async def get_activity_log(run_id: str, last: int = 50):
    """Get the activity feed for a run. Returns the most recent `last` entries."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    all_activity = state_values.get("activity_log", [])
    return {
        "activity": all_activity[-last:],
        "total": len(all_activity),
    }


@router.post("/runs/{run_id}/hitl")
async def submit_hitl_decision(run_id: str, decision: HITLDecision):
    """
    Submit a HITL decision (approve/reject/request changes).
    
    - Accepts the decision, updates LangGraph state, resumes pipeline in background
    - Returns immediately (does NOT wait for pipeline to finish)
    - Handles double-submit gracefully (if already past the gate, returns 200 with info)
    """
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    current_state = app.get_state(config)
    state_values = current_state.values
    next_nodes = current_state.next

    # Determine which gate we're at
    at_gate_1 = "hitl_gate_1" in next_nodes
    at_gate_2 = "hitl_gate_2" in next_nodes

    if not at_gate_1 and not at_gate_2:
        # Not at a gate — maybe already approved, or pipeline is running
        # Return gracefully instead of 400 error
        return {
            "run_id": run_id,
            "status": "already_processed",
            "current_phase": state_values.get("current_phase", "unknown"),
            "message": f"Run is not at a HITL gate (already past it or still running). Next: {next_nodes}",
            "next_steps": next_nodes,
        }

    if at_gate_1:
        state_update = {
            "hitl_gate1_status": decision.decision,
            "hitl_gate1_feedback": decision.feedback or "",
            "status": "running",
            "planning_feedback": decision.feedback or "",
        }
        if decision.decision in ("rejected", "changes_requested"):
            state_update["planning_converged"] = False
            state_update["planning_iteration"] = max(0, state_values.get("planning_iteration", 1) - 1)
    else:  # at_gate_2
        state_update = {
            "hitl_gate2_status": decision.decision,
            "hitl_gate2_feedback": decision.feedback or "",
            "status": "running",
        }

    # Update state
    app.update_state(config, state_update)

    print(f"\n🚦 HITL Decision: {decision.decision}")
    if decision.feedback:
        print(f"   Feedback: {decision.feedback}")
    print(f"{'='*60}\n")

    # Resume pipeline in background — returns immediately
    task = asyncio.create_task(_run_pipeline_background(run_id))
    _running_tasks[run_id] = task

    return {
        "run_id": run_id,
        "status": "running",
        "current_phase": "building" if at_gate_1 else "devops",
        "message": f"Decision '{decision.decision}' applied. Pipeline resumed in background.",
        "next_steps": [],
    }


@router.get("/runs")
async def list_runs():
    """List all runs with derived status."""
    app = get_workflow()
    summaries = []

    for run_id, run_data in runs_store.items():
        config = run_data["config"]
        try:
            current_state = app.get_state(config)
            state_values = current_state.values
            derived = _derive_run_status(run_id, state_values, current_state.next)

            summaries.append({
                "run_id": run_id,
                "brief": state_values.get("brief", "")[:100],
                "status": derived["status"],
                "current_phase": derived["current_phase"],
                "num_requirements": len(state_values.get("requirements", [])),
                "num_user_stories": len(state_values.get("user_stories", [])),
                "num_generated_files": len(state_values.get("generated_files", [])),
            })
        except Exception:
            summaries.append({
                "run_id": run_id,
                "brief": "",
                "status": "initializing",
                "current_phase": "planning",
                "num_requirements": 0,
                "num_user_stories": 0,
                "num_generated_files": 0,
            })

    return {"runs": summaries}


# ============================================================
# Export: Write generated files to disk + ZIP
# ============================================================

import os
import shutil
import zipfile
from fastapi.responses import FileResponse

EXPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app")


@router.post("/runs/{run_id}/export")
async def export_project(run_id: str):
    """Export all generated files to app/ folder + ZIP."""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    app = get_workflow()
    config = runs_store[run_id]["config"]
    state_values = app.get_state(config).values

    all_files = list(state_values.get("generated_files", []))
    all_files.extend(state_values.get("docker_files", []))

    if not all_files:
        raise HTTPException(status_code=400, detail="No files to export. Run the pipeline first.")

    if os.path.exists(APP_DIR):
        shutil.rmtree(APP_DIR)
    os.makedirs(APP_DIR, exist_ok=True)

    written = []
    errors = []
    for f in all_files:
        file_path = os.path.join(APP_DIR, f["path"])
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(f["content"])
            written.append(f["path"])
        except Exception as e:
            errors.append({"path": f["path"], "error": str(e)})

    # Write artifacts.json
    artifacts_path = os.path.join(APP_DIR, "artifacts.json")
    artifacts = {
        "requirements": state_values.get("requirements", []),
        "inception": state_values.get("inception"),
        "user_stories": state_values.get("user_stories", []),
        "test_cases": state_values.get("test_cases", []),
        "decisions_log": state_values.get("decisions_log", []),
        "integration_score": state_values.get("integration_score", 0),
        "integration_issues": state_values.get("integration_issues", []),
    }
    with open(artifacts_path, "w", encoding="utf-8") as fh:
        json.dump(artifacts, fh, indent=2, ensure_ascii=False, default=str)
    written.append("artifacts.json")

    # Write tech spec
    tech_spec = state_values.get("tech_spec", {})
    if tech_spec:
        tech_spec_path = os.path.join(APP_DIR, "tech_spec.json")
        with open(tech_spec_path, "w", encoding="utf-8") as fh:
            json.dump(tech_spec, fh, indent=2, ensure_ascii=False, default=str)
        written.append("tech_spec.json")

    # Write Mermaid diagrams
    mermaid_er = tech_spec.get("mermaid_er", "")
    if mermaid_er:
        mmd_path = os.path.join(APP_DIR, "docs", "er_diagram.mmd")
        os.makedirs(os.path.dirname(mmd_path), exist_ok=True)
        with open(mmd_path, "w", encoding="utf-8") as fh:
            fh.write(mermaid_er)
        written.append("docs/er_diagram.mmd")

    for i, seq in enumerate(tech_spec.get("mermaid_sequence", [])):
        title = seq.get("title", f"sequence_{i+1}").replace(" ", "_").lower()
        mmd_path = os.path.join(APP_DIR, "docs", f"{title}.mmd")
        os.makedirs(os.path.dirname(mmd_path), exist_ok=True)
        with open(mmd_path, "w", encoding="utf-8") as fh:
            fh.write(seq.get("code", ""))
        written.append(f"docs/{title}.mmd")

    # Create ZIP
    os.makedirs(EXPORT_BASE_DIR, exist_ok=True)
    zip_path = os.path.join(EXPORT_BASE_DIR, f"{run_id}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(APP_DIR):
            for file in files:
                file_full = os.path.join(root, file)
                arcname = os.path.relpath(file_full, APP_DIR)
                zf.write(file_full, arcname)

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)

    return {
        "status": "exported",
        "run_id": run_id,
        "app_dir": APP_DIR,
        "zip_download": f"/api/runs/{run_id}/download",
        "files_written": len(written),
        "files": written,
        "errors": errors,
        "zip_size_mb": round(zip_size_mb, 2),
        "ready_to_deploy": os.path.exists(os.path.join(APP_DIR, "docker-compose.yml")),
    }


@router.get("/runs/{run_id}/download")
async def download_project(run_id: str):
    """Download the exported project as a ZIP file."""
    zip_path = os.path.join(EXPORT_BASE_DIR, f"{run_id}.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Export not found. Call POST /api/runs/{run_id}/export first.")
    return FileResponse(path=zip_path, filename=f"project-{run_id}.zip", media_type="application/zip")


# ============================================================
# Deploy: docker-compose / podman-compose up in app/ folder
# ============================================================

deploy_state = {
    "status": "idle",
    "process": None,
    "logs": [],
    "urls": {},
    "compose_cmd": None,
}


def _find_compose_command() -> list[str] | None:
    """Detect available compose command: podman-compose, docker-compose, or docker compose."""
    import shutil
    if shutil.which("podman-compose"):
        return ["podman-compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    return None


@router.get("/deploy/check")
async def deploy_check():
    """Check if a compose tool is available and Docker/Podman is running."""
    compose_cmd = _find_compose_command()
    compose_path = os.path.join(APP_DIR, "docker-compose.yml")
    has_export = os.path.exists(compose_path)

    if not compose_cmd:
        return {
            "ready": False,
            "has_export": has_export,
            "compose_tool": None,
            "message": "No se encontró docker-compose ni podman-compose. Instala Docker Desktop o Podman y asegúrate de que esté corriendo.",
            "instructions": [
                "1. Instala Docker Desktop (https://docker.com) o Podman (https://podman.io)",
                "2. Asegúrate de que el servicio esté corriendo",
                "3. Para Podman: pip install podman-compose",
                "4. Intenta de nuevo",
            ],
        }

    return {
        "ready": has_export,
        "has_export": has_export,
        "compose_tool": " ".join(compose_cmd),
        "message": f"Listo. Usando {''.join(compose_cmd)}." if has_export else "Exporta un run primero.",
    }


class DeployRequest(BaseModel):
    anthropic_api_key: Optional[str] = ""


@router.post("/deploy")
async def deploy_app(request: DeployRequest = DeployRequest()):
    """Run compose up --build in the app/ directory. Auto-detects podman-compose or docker-compose."""
    global deploy_state

    compose_path = os.path.join(APP_DIR, "docker-compose.yml")
    if not os.path.exists(compose_path):
        raise HTTPException(status_code=400, detail="No docker-compose.yml en app/. Exporta un run primero.")

    compose_cmd = _find_compose_command()
    if not compose_cmd:
        raise HTTPException(
            status_code=400,
            detail="No se encontró docker-compose ni podman-compose. Instala Docker Desktop o Podman y asegúrate de que esté corriendo. Para Podman: pip install podman-compose",
        )

    if deploy_state["status"] == "running":
        return {"status": "already_running", "urls": deploy_state["urls"], "message": "App ya está corriendo."}

    deploy_state["status"] = "building"
    deploy_state["logs"] = []
    deploy_state["compose_cmd"] = " ".join(compose_cmd)

    # Write .env file in app/ with the API key so docker-compose picks it up
    api_key = (request.anthropic_api_key or "").strip()
    env_path = os.path.join(APP_DIR, ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"ANTHROPIC_API_KEY={api_key}\n")
    if api_key:
        print(f"  🔑 API key written to app/.env ({len(api_key)} chars)")
    else:
        print(f"  ⚠️  No API key provided — GenAI will use fallback mode")

    cmd = compose_cmd + ["up", "--build", "-d"]
    print(f"\n🚀 Deploy: {' '.join(cmd)} in {APP_DIR}")

    try:
        # Pass API key as env var to subprocess as well (belt + suspenders)
        env = {**os.environ}
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=APP_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""
        deploy_state["logs"].append(stdout_text)
        if stderr_text:
            deploy_state["logs"].append(stderr_text)

        if process.returncode != 0:
            deploy_state["status"] = "error"
            # Parse common errors
            error_msg = stderr_text[-2000:]
            if "npm ci" in error_msg:
                error_msg += "\n\n💡 Tip: El Dockerfile del frontend usa 'npm ci' pero no hay package-lock.json. Cambia a 'npm install'."
            if "HEALTHCHECK" in error_msg:
                error_msg += "\n\n💡 Tip: Podman no soporta HEALTHCHECK en formato OCI. Elimínalo del Dockerfile."
            return {"status": "error", "message": f"Build falló ({' '.join(compose_cmd)})", "logs": error_msg}

        await asyncio.sleep(3)
        deploy_state["status"] = "running"
        deploy_state["urls"] = {
            "frontend": "http://localhost:3000",
            "backend": "http://localhost:8001",
            "api_docs": "http://localhost:8001/docs",
        }
        return {
            "status": "running",
            "urls": deploy_state["urls"],
            "compose_tool": " ".join(compose_cmd),
            "message": f"App desplegada con {' '.join(compose_cmd)}.",
        }

    except asyncio.TimeoutError:
        deploy_state["status"] = "error"
        return {"status": "error", "message": "Build timeout (10 min). Revisa los logs de Docker/Podman."}
    except FileNotFoundError:
        deploy_state["status"] = "error"
        return {
            "status": "error",
            "message": f"Comando '{' '.join(compose_cmd)}' no encontrado. ¿Está Docker/Podman instalado y corriendo?",
        }
    except Exception as e:
        deploy_state["status"] = "error"
        return {"status": "error", "message": str(e)}


@router.post("/teardown")
async def teardown_app():
    """Stop and remove all containers."""
    global deploy_state
    compose_path = os.path.join(APP_DIR, "docker-compose.yml")
    if not os.path.exists(compose_path):
        return {"status": "nothing_to_teardown", "message": "No hay app desplegada."}

    compose_cmd = _find_compose_command()
    if not compose_cmd:
        return {"status": "error", "message": "No se encontró docker-compose ni podman-compose."}

    try:
        cmd = compose_cmd + ["down", "-v", "--remove-orphans"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=APP_DIR, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(process.communicate(), timeout=60)
        deploy_state["status"] = "idle"
        deploy_state["urls"] = {}
        return {"status": "stopped", "message": "Contenedores detenidos y eliminados."}
    except Exception as e:
        return {"status": "error", "message": f"Teardown falló: {str(e)}"}


@router.get("/deploy/status")
async def deploy_status():
    """Get current deployment status."""
    return {
        "status": deploy_state["status"],
        "urls": deploy_state["urls"],
        "compose_tool": deploy_state.get("compose_cmd"),
        "logs": deploy_state["logs"][-5:] if deploy_state["logs"] else [],
    }
