"""
AI Dev Team - LangGraph State Definition

Shared state that flows through the agent pipeline.
Uses Annotated reducers for fields written by parallel nodes (generated_files, decisions_log).
"""

from typing import TypedDict, Literal, Optional, Annotated
from datetime import datetime
import operator


# --- Reducer functions for parallel writes ---

def merge_files(existing: list, new: list) -> list:
    """Merge generated files — new files override existing by path."""
    merged = {f["path"]: f for f in existing}
    for f in new:
        merged[f["path"]] = f
    return list(merged.values())


def merge_append(existing: list, new: list) -> list:
    """Simple append for logs, test cases, etc."""
    return existing + new


def last_non_empty_str(existing: str, new: str) -> str:
    """Reducer for current_agent / current_phase: keeps the last non-empty value.
    
    This allows parallel nodes (backend_builder ∥ frontend_builder) to
    skip writing these fields without triggering InvalidUpdateError.
    When a node DOES write a value, it wins over the previous one.
    """
    return new if new else existing


# --- Artifact Models ---

class Requirement(TypedDict):
    id: str
    title: str
    description: str
    type: str
    priority: str
    domain: str
    created_by: str
    iteration: int


class InceptionItem(TypedDict):
    id: str
    mvp_scope: list[str]
    out_of_scope: list[str]
    risks: list[dict]
    success_metrics: list[str]
    tech_constraints: list[str]
    created_by: str
    iteration: int


class UserStory(TypedDict):
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    req_ids: list[str]
    domain: str
    priority: str
    story_points: int
    created_by: str
    iteration: int


class TestCase(TypedDict):
    id: str
    title: str
    description: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    us_id: str
    type: str
    created_by: str


class TechSpec(TypedDict):
    project_structure: dict
    data_models: list[dict]
    api_endpoints: list[dict]
    db_schema: str
    ml_pipeline: dict
    genai_integration: dict
    mermaid_er: str
    mermaid_sequence: list[dict]
    stack: dict
    created_by: str
    iteration: int


class GeneratedFile(TypedDict):
    path: str
    content: str
    us_ids: list[str]
    created_by: str


class ActivityEntry(TypedDict):
    timestamp: str
    agent: str
    icon: str
    message: str
    detail: str


class DecisionLogEntry(TypedDict):
    timestamp: str
    agent: str
    phase: str
    decision: str
    justification: str
    artifacts_affected: list[str]
    iteration: int


# --- Main Graph State ---

class AgentState(TypedDict):
    """
    Shared state for the AI Dev Team pipeline.
    
    Fields with Annotated[..., reducer] support parallel writes
    from concurrent nodes (e.g., backend + frontend builders).
    """
    
    # Run metadata
    run_id: str
    brief: str
    current_phase: Annotated[str, last_non_empty_str]
    current_agent: Annotated[str, last_non_empty_str]
    next_agent: Annotated[str, last_non_empty_str]
    status: Annotated[str, last_non_empty_str]
    
    # Phase 1: Planning (iterative cycle)
    requirements: list[Requirement]
    inception: Optional[InceptionItem]
    user_stories: list[UserStory]
    tech_spec: Optional[TechSpec]
    backend_spec: Optional[dict]
    frontend_spec: Optional[dict]
    qa_spec: Optional[dict]
    devops_spec: Optional[dict]
    planning_iteration: int
    planning_max_iterations: int
    planning_feedback: str
    planning_converged: bool
    
    # HITL Gate 1
    hitl_gate1_status: str
    hitl_gate1_feedback: str
    
    # Phase 2: Building — Annotated reducers for parallel writes
    generated_files: Annotated[list[GeneratedFile], merge_files]
    test_cases: Annotated[list[TestCase], merge_append]
    test_results: Optional[dict]
    
    # Integration Validation
    integration_valid: bool
    integration_score: int
    integration_issues: list[dict]
    integration_fixes: list[dict]
    integration_iteration: int
    integration_max_iterations: int
    
    # HITL Gate 2
    hitl_gate2_status: str
    hitl_gate2_feedback: str
    
    # Phase 3: DevOps
    docker_files: list[GeneratedFile]
    deployment_ready: bool
    
    # Diagrams
    er_diagram_svg: str
    sequence_diagrams_svg: list[dict]
    
    # Decision log — Annotated for parallel append
    decisions_log: Annotated[list[DecisionLogEntry], merge_append]
    
    # Activity feed — live messages from agents (Annotated for parallel append)
    activity_log: Annotated[list[ActivityEntry], merge_append]
    
    # Error handling
    errors: Annotated[list[dict], merge_append]
    retry_count: int


def create_initial_state(run_id: str, brief: str) -> AgentState:
    """Create the initial state for a new run."""
    return AgentState(
        run_id=run_id,
        brief=brief,
        current_phase="planning",
        current_agent="",
        next_agent="ba_agent",
        status="running",
        
        requirements=[],
        inception=None,
        user_stories=[],
        tech_spec=None,
        backend_spec=None,
        frontend_spec=None,
        qa_spec=None,
        devops_spec=None,
        planning_iteration=0,
        planning_max_iterations=3,
        planning_feedback="",
        planning_converged=False,
        
        hitl_gate1_status="pending",
        hitl_gate1_feedback="",
        
        generated_files=[],
        test_cases=[],
        test_results=None,
        
        hitl_gate2_status="pending",
        hitl_gate2_feedback="",
        
        integration_valid=False,
        integration_score=0,
        integration_issues=[],
        integration_fixes=[],
        integration_iteration=0,
        integration_max_iterations=2,
        
        docker_files=[],
        deployment_ready=False,
        
        er_diagram_svg="",
        sequence_diagrams_svg=[],
        
        decisions_log=[],
        activity_log=[],
        
        errors=[],
        retry_count=0,
    )


def log_decision(
    state: AgentState,
    agent: str,
    phase: str,
    decision: str,
    justification: str,
    artifacts: list[str]
) -> DecisionLogEntry:
    """Helper to create a decision log entry."""
    return DecisionLogEntry(
        timestamp=datetime.now().isoformat(),
        agent=agent,
        phase=phase,
        decision=decision,
        justification=justification,
        artifacts_affected=artifacts,
        iteration=state.get("planning_iteration", 0),
    )


def activity(agent: str, icon: str, message: str, detail: str = "") -> ActivityEntry:
    """Helper to create an activity feed entry."""
    return ActivityEntry(
        timestamp=datetime.now().isoformat(),
        agent=agent,
        icon=icon,
        message=message,
        detail=detail,
    )
