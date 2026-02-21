"""
AI Dev Team - Graph Nodes

Each node wraps an agent call. Nodes receive state, invoke their agent,
and return state updates.

Builder nodes (backend, frontend) are designed for parallel execution:
- Each writes to generated_files via the merge_files reducer
- Each appends to decisions_log via merge_append

Agent descriptions follow LangChain best practices:
clear, action-oriented names with specific capability descriptions.
"""

from datetime import datetime
from .state import AgentState, log_decision, activity


# =============================================================================
# AGENT REGISTRY (descriptions for orchestration / documentation)
# =============================================================================

AGENT_REGISTRY = {
    "ba_agent": {
        "name": "Business Analyst",
        "description": "Analyzes the project brief and extracts functional/non-functional requirements with domain classification and priority.",
        "phase": "planning",
    },
    "po_agent": {
        "name": "Product Owner",
        "description": "Defines MVP scope, creates prioritized user stories with acceptance criteria, and manages risk assessment.",
        "phase": "planning",
    },
    "architect_agent": {
        "name": "Software Architect",
        "description": "Designs system architecture: data models, API endpoints, DB schema, ML pipeline, GenAI integration. Produces separate specs for each builder team.",
        "phase": "planning",
    },
    "planning_evaluator": {
        "name": "Planning Evaluator",
        "description": "Evaluates if planning artifacts (requirements, stories, tech spec) are complete and consistent. Decides if another iteration is needed.",
        "phase": "planning",
    },
    "backend_builder": {
        "name": "Backend Developer",
        "description": "Generates Python/FastAPI backend code file-by-file from architect's backend_spec. Handles models, schemas, routers, services, auth, ML, and GenAI integration.",
        "phase": "building",
    },
    "frontend_builder": {
        "name": "Frontend Developer",
        "description": "Generates React/Vite/TailwindCSS frontend code file-by-file from architect's frontend_spec. Handles components, pages, services, routing, and API integration.",
        "phase": "building",
    },
    "qa_agent": {
        "name": "QA Engineer",
        "description": "Generates pytest test files from architect's qa_spec. Creates integration tests, unit tests, and acceptance tests for all API endpoints and services.",
        "phase": "qa",
    },
    "integration_validator": {
        "name": "Integration Validator (Architect)",
        "description": "Cross-validates all generated files for consistency: imports match actual files, API endpoints align between frontend/backend, schemas match models.",
        "phase": "integration",
    },
    "devops_agent": {
        "name": "DevOps Engineer",
        "description": "Generates Dockerfiles, docker-compose, nginx config, init scripts, and README from architect's devops_spec. Podman-compatible.",
        "phase": "devops",
    },
}


# =============================================================================
# PHASE 1: PLANNING NODES
# =============================================================================

async def ba_node(state: AgentState) -> dict:
    """Business Analyst: Analyzes brief, generates requirements."""
    from ..agents.ba_agent import run_ba_agent

    iteration = state['planning_iteration'] + 1
    print(f"\n{'='*60}")
    print(f"🔍 BA Agent - Iteration {iteration}")
    print(f"{'='*60}")

    activities = [activity("BA Agent", "🔍", "Analizando brief...", f"Iteración {iteration}")]

    result = await run_ba_agent(state)

    reqs = result['requirements']
    must = sum(1 for r in reqs if r.get('priority') == 'must')
    should = sum(1 for r in reqs if r.get('priority') == 'should')
    could = sum(1 for r in reqs if r.get('priority') == 'could')
    domains = set(r.get('domain', '') for r in reqs)

    activities.append(activity("BA Agent", "✅", f"{len(reqs)} requerimientos identificados", f"{must} must, {should} should, {could} could · Dominios: {', '.join(domains)}"))

    decision = log_decision(
        state,
        agent="BA Agent",
        phase="planning",
        decision=f"Generated {len(reqs)} requirements",
        justification=result.get("reasoning", "Analysis of brief"),
        artifacts=[r["id"] for r in reqs],
    )

    return {
        "requirements": reqs,
        "current_agent": "ba_agent",
        "decisions_log": [decision],
        "activity_log": activities,
    }


async def po_node(state: AgentState) -> dict:
    """Product Owner: Defines MVP, generates user stories."""
    from ..agents.po_agent import run_po_agent

    iteration = state['planning_iteration'] + 1
    print(f"\n{'='*60}")
    print(f"📋 Product Owner Agent - Iteration {iteration}")
    print(f"{'='*60}")

    activities = [activity("PO Agent", "📋", "Priorizando requerimientos y definiendo MVP...")]

    result = await run_po_agent(state)

    inception = result["inception"]
    stories = result["user_stories"]
    total_points = sum(us.get("story_points", 0) for us in stories)

    activities.append(activity("PO Agent", "🎯", f"MVP definido: {len(inception.get('mvp_scope', []))} en scope, {len(inception.get('out_of_scope', []))} fuera", f"{len(inception.get('risks', []))} riesgos identificados"))
    activities.append(activity("PO Agent", "✅", f"{len(stories)} historias de usuario generadas", f"{total_points} story points totales"))

    us_ids = [us["id"] for us in stories]
    decision = log_decision(
        state,
        agent="Product Owner Agent",
        phase="planning",
        decision=f"Defined MVP with {len(us_ids)} user stories",
        justification=result.get("reasoning", "MVP prioritization"),
        artifacts=[inception["id"]] + us_ids,
    )

    return {
        "inception": inception,
        "user_stories": stories,
        "current_agent": "po_agent",
        "decisions_log": [decision],
        "activity_log": activities,
    }


async def architect_node(state: AgentState) -> dict:
    """Architect: Generates tech spec + separate specs per builder (5 LLM calls)."""
    from ..agents.architect_agent import run_architect_agent

    iteration = state['planning_iteration'] + 1
    print(f"\n{'='*60}")
    print(f"🏗️  Architect Agent - Iteration {iteration}")
    print(f"{'='*60}")

    activities = [activity("Architect", "🏗️", "Diseñando arquitectura técnica...", f"Iteración {iteration}")]

    result = await run_architect_agent(state)

    ts = result["tech_spec"]
    n_files = len(ts.get("project_structure", {}).get("files", []))
    n_models = len(ts.get("data_models", []))
    n_endpoints = len(ts.get("api_endpoints", []))

    activities.append(activity("Architect", "📐", f"Tech spec: {n_files} archivos, {n_models} modelos, {n_endpoints} endpoints"))

    specs_generated = []
    if result.get("backend_spec"): specs_generated.append("backend")
    if result.get("frontend_spec"): specs_generated.append("frontend")
    if result.get("qa_spec"): specs_generated.append("QA")
    if result.get("devops_spec"): specs_generated.append("DevOps")
    activities.append(activity("Architect", "✅", f"Specs generadas para: {', '.join(specs_generated)}"))

    decision = log_decision(
        state,
        agent="Architect Agent",
        phase="planning",
        decision=f"Tech spec generated. Feasibility: {result.get('feasibility', 'approved')}",
        justification=result.get("reasoning", "Technical analysis"),
        artifacts=["tech_spec", "backend_spec", "frontend_spec", "qa_spec", "devops_spec"],
    )

    return {
        "tech_spec": ts,
        "backend_spec": result.get("backend_spec"),
        "frontend_spec": result.get("frontend_spec"),
        "qa_spec": result.get("qa_spec"),
        "devops_spec": result.get("devops_spec"),
        "er_diagram_svg": result.get("er_diagram_svg", ""),
        "sequence_diagrams_svg": result.get("sequence_diagrams_svg", []),
        "current_agent": "architect_agent",
        "decisions_log": [decision],
        "activity_log": activities,
    }


async def planning_evaluator_node(state: AgentState) -> dict:
    """Evaluates if planning has converged or needs another iteration."""
    from ..agents.evaluator import evaluate_planning

    iteration = state['planning_iteration'] + 1
    print(f"\n{'='*60}")
    print(f"⚖️  Planning Evaluator - Iteration {iteration}")
    print(f"{'='*60}")

    activities = [activity("Evaluator", "⚖️", "Evaluando calidad de planificación...", f"Iteración {iteration}")]

    result = await evaluate_planning(state)

    new_iteration = state["planning_iteration"] + 1
    converged = result["converged"] or new_iteration >= state["planning_max_iterations"]

    if converged:
        print(f"✅ Planning converged after {new_iteration} iteration(s)")
        activities.append(activity("Evaluator", "✅", f"Planificación aprobada en iteración {new_iteration}", result.get("feedback", "")))
    else:
        print(f"🔄 Planning needs refinement. Feedback: {result['feedback']}")
        activities.append(activity("Evaluator", "🔄", f"Requiere refinamiento — iteración {new_iteration}", result.get("feedback", "")[:200]))

    decision = log_decision(
        state,
        agent="Planning Evaluator",
        phase="planning",
        decision="converged" if converged else "needs_refinement",
        justification=result.get("feedback", "Evaluation complete"),
        artifacts=[],
    )

    return {
        "planning_iteration": new_iteration,
        "planning_converged": converged,
        "planning_feedback": result.get("feedback", ""),
        "decisions_log": [decision],
        "activity_log": activities,
    }


# =============================================================================
# HITL GATES
# =============================================================================

async def hitl_gate1_node(state: AgentState) -> dict:
    """HITL Gate 1: Pauses for human approval of planning artifacts."""
    print(f"\n{'='*60}")
    print(f"🚦 HITL Gate 1 - Awaiting human approval")
    print(f"{'='*60}")

    decision = log_decision(
        state, agent="HITL Gate 1", phase="planning",
        decision="Waiting for human approval",
        justification="Planning phase complete, artifacts ready for review",
        artifacts=[r["id"] for r in state["requirements"]] + [us["id"] for us in state["user_stories"]],
    )

    return {
        "status": "waiting_hitl",
        "current_phase": "hitl_gate_1",
        "current_agent": "hitl_gate_1",
        "decisions_log": [decision],
        "activity_log": [activity("HITL Gate 1", "🚦", "Esperando aprobación humana", f"{len(state['requirements'])} reqs, {len(state['user_stories'])} US listos para revisión")],
    }


async def hitl_gate2_node(state: AgentState) -> dict:
    """HITL Gate 2: Pauses for human approval of built artifacts."""
    print(f"\n{'='*60}")
    print(f"🚦 HITL Gate 2 - Awaiting human approval")
    print(f"{'='*60}")

    decision = log_decision(
        state, agent="HITL Gate 2", phase="building",
        decision="Waiting for human approval",
        justification="Build phase complete, code and tests ready for review",
        artifacts=[f["path"] for f in state["generated_files"]] + [tc["id"] for tc in state["test_cases"]],
    )

    return {
        "status": "waiting_hitl",
        "current_phase": "hitl_gate_2",
        "current_agent": "hitl_gate_2",
        "decisions_log": [decision],
        "activity_log": [activity("HITL Gate 2", "🚦", "Esperando aprobación humana", f"{len(state['generated_files'])} archivos, {len(state['test_cases'])} tests listos para revisión")],
    }


# =============================================================================
# PHASE 2: BUILDING NODES (parallel-ready)
# =============================================================================

async def backend_builder_node(state: AgentState) -> dict:
    """Backend Developer subagent. Runs in parallel with frontend_builder_node."""
    from ..agents.backend_builder import run_backend_builder

    print(f"\n{'='*60}")
    print(f"⚙️  Backend Builder Agent (parallel)")
    print(f"{'='*60}")

    fix_instructions = _get_fix_instructions(state, "backend_builder")
    mode = "fix" if fix_instructions else "build"
    activities = [activity("Backend Builder", "🐍", "Generando código backend..." if not fix_instructions else f"Corrigiendo {len(fix_instructions)} archivos backend...")]

    result = await run_backend_builder(state, fix_instructions=fix_instructions)

    files = result["files"]
    total_lines = sum(f["content"].count("\n") + 1 for f in files)
    activities.append(activity("Backend Builder", "✅", f"{len(files)} archivos backend generados", f"~{total_lines} líneas de código"))

    decision = log_decision(
        state, agent="Backend Builder", phase="building",
        decision=f"Generated {len(files)} backend files" + (" (fix)" if fix_instructions else ""),
        justification=result.get("reasoning", "Backend implementation"),
        artifacts=[f["path"] for f in files],
    )

    return {
        "generated_files": files,
        "decisions_log": [decision],
        "activity_log": activities,
    }


async def frontend_builder_node(state: AgentState) -> dict:
    """Frontend Developer subagent. Runs in parallel with backend_builder_node."""
    from ..agents.frontend_builder import run_frontend_builder

    print(f"\n{'='*60}")
    print(f"🎨 Frontend Builder Agent (parallel)")
    print(f"{'='*60}")

    fix_instructions = _get_fix_instructions(state, "frontend_builder")
    activities = [activity("Frontend Builder", "⚛️", "Generando código frontend..." if not fix_instructions else f"Corrigiendo {len(fix_instructions)} archivos frontend...")]

    result = await run_frontend_builder(state, fix_instructions=fix_instructions)

    files = result["files"]
    total_lines = sum(f["content"].count("\n") + 1 for f in files)
    activities.append(activity("Frontend Builder", "✅", f"{len(files)} archivos frontend generados", f"~{total_lines} líneas de código"))

    decision = log_decision(
        state, agent="Frontend Builder", phase="building",
        decision=f"Generated {len(files)} frontend files" + (" (fix)" if fix_instructions else ""),
        justification=result.get("reasoning", "Frontend implementation"),
        artifacts=[f["path"] for f in files],
    )

    return {
        "generated_files": files,
        "decisions_log": [decision],
        "activity_log": activities,
    }


async def qa_node(state: AgentState) -> dict:
    """QA Engineer: Generates test files. Runs after builders complete."""
    from ..agents.qa_agent import run_qa_agent

    print(f"\n{'='*60}")
    print(f"🧪 QA Agent")
    print(f"{'='*60}")

    activities = [activity("QA Agent", "🧪", "Generando casos de prueba y archivos de test...")]

    result = await run_qa_agent(state)

    tc_ids = [tc["id"] for tc in result["test_cases"]]
    n_files = len(result.get("test_files", []))
    activities.append(activity("QA Agent", "✅", f"{len(tc_ids)} test cases, {n_files} archivos de test generados"))

    decision = log_decision(
        state, agent="QA Agent", phase="qa",
        decision=f"Generated {len(tc_ids)} test cases",
        justification=result.get("reasoning", "Test case generation"),
        artifacts=tc_ids,
    )

    return {
        "test_cases": result["test_cases"],
        "test_results": result.get("test_results"),
        "generated_files": result.get("test_files", []),
        "current_agent": "qa_agent",
        "decisions_log": [decision],
        "activity_log": activities,
    }


# =============================================================================
# INTEGRATION VALIDATION
# =============================================================================

async def integration_validator_node(state: AgentState) -> dict:
    """Architect cross-validates all generated code for consistency."""
    from ..agents.integration_validator import run_integration_validator

    iteration = state.get("integration_iteration", 0) + 1

    print(f"\n{'='*60}")
    print(f"🔍 Integration Validator (Architect) - Iteration {iteration}")
    print(f"{'='*60}")

    activities = [activity("Integration Validator", "🔗", f"Validando consistencia cruzada...", f"Iteración {iteration}, {len(state.get('generated_files', []))} archivos")]

    result = await run_integration_validator(state)

    is_consistent = result["is_consistent"]
    score = result.get("score", 0)
    file_fixes = result.get("file_fixes", [])

    if is_consistent:
        activities.append(activity("Integration Validator", "✅", f"Integración válida — score {score}/100"))
    else:
        activities.append(activity("Integration Validator", "🔧", f"Score {score}/100 — {len(file_fixes)} archivos necesitan corrección", result.get("summary", "")[:150]))

    decision = log_decision(
        state, agent="Integration Validator (Architect)", phase="integration",
        decision=f"Score: {score}/100. {'PASSED' if is_consistent else f'FAILED - {len(file_fixes)} fixes'}",
        justification=result.get("summary", ""),
        artifacts=[fix["path"] for fix in file_fixes],
    )

    return {
        "integration_valid": is_consistent,
        "integration_score": score,
        "integration_issues": result.get("issues", []),
        "integration_fixes": file_fixes,
        "integration_iteration": iteration,
        "current_agent": "integration_validator",
        "decisions_log": [decision],
        "activity_log": activities,
    }


def _get_fix_instructions(state: AgentState, builder_name: str) -> list:
    """Get fix instructions for a specific builder from integration validator."""
    fixes = state.get("integration_fixes", [])
    return [f for f in fixes if f.get("builder") == builder_name]


# =============================================================================
# PHASE 3: DEVOPS
# =============================================================================

async def devops_node(state: AgentState) -> dict:
    """DevOps Engineer: Generates Docker/compose/infra files."""
    from ..agents.devops_agent import run_devops_agent

    print(f"\n{'='*60}")
    print(f"🚀 DevOps Agent")
    print(f"{'='*60}")

    activities = [activity("DevOps Agent", "🚀", "Generando configuración de despliegue...", "Dockerfile, docker-compose, nginx, README")]

    result = await run_devops_agent(state)

    files = result["files"]
    file_names = [f["path"].split("/")[-1] for f in files]
    activities.append(activity("DevOps Agent", "✅", f"{len(files)} archivos de infraestructura generados", ", ".join(file_names)))
    activities.append(activity("Pipeline", "🏁", "Pipeline completado", "Proyecto listo para exportar y desplegar"))

    decision = log_decision(
        state, agent="DevOps Agent", phase="devops",
        decision="Generated deployment configuration",
        justification=result.get("reasoning", "Deployment setup"),
        artifacts=[f["path"] for f in files],
    )

    return {
        "docker_files": files,
        "deployment_ready": True,
        "current_phase": "done",
        "status": "completed",
        "current_agent": "devops_agent",
        "decisions_log": [decision],
        "activity_log": activities,
    }


# =============================================================================
# CONDITIONAL EDGES
# =============================================================================

def should_continue_planning(state: AgentState) -> str:
    """Decides if planning needs another iteration or moves to HITL."""
    if state["planning_converged"]:
        return "hitl_gate_1"
    else:
        return "ba_node"


def should_fix_or_continue(state: AgentState) -> str:
    """
    After integration validation:
    - consistent → HITL Gate 2
    - not consistent, under max → fix cycle (fan-out to parallel builders again)
    - max iterations → force continue
    """
    is_consistent = state.get("integration_valid", False)
    iteration = state.get("integration_iteration", 0)
    max_iterations = state.get("integration_max_iterations", 2)

    if is_consistent:
        print(f"  ✅ Integration valid → HITL Gate 2")
        return "hitl_gate_2"
    elif iteration >= max_iterations:
        print(f"  ⚠️  Max fix iterations ({max_iterations}) reached → forcing HITL Gate 2")
        return "hitl_gate_2"
    else:
        print(f"  🔄 Fix cycle {iteration}/{max_iterations} → parallel rebuild")
        return "fan_out_builders"
