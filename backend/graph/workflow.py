"""
AI Dev Team - LangGraph Workflow Definition

Multi-agent pipeline with:
- Sequential planning cycle (BA → PO → Architect → Evaluator)
- Parallel building phase (Backend ∥ Frontend → QA)
- Integration validation with fix loop
- DevOps packaging

Pattern: Subagents with fan-out parallelization (LangChain best practice).
Backend and Frontend builders run as isolated subagents in parallel,
each with their own context (backend_spec / frontend_spec from Architect).

Graph:

    START
      │
      ▼
    [BA] → [PO] → [Architect (5 calls)] → [Evaluator]
      ▲                                        │
      └──── if not converged ◄────────────────┘
                                               │ converged
                                               ▼
                                        [HITL Gate 1] ← interrupt
                                               │ approved
                                               ▼
                                        [fan_out_builders]
                                          ┌────┴────┐
                                          │         │
                                          ▼         ▼
                                    [Backend]   [Frontend]   ← PARALLEL
                                          │         │
                                          └────┬────┘
                                               ▼
                                            [QA]
                                               │
                                               ▼
                                    [Integration Validator]
                                          │           │
                                      fix ◄           │ valid
                                          │           ▼
                                   [fan_out_builders] [HITL Gate 2] ← interrupt
                                                      │ approved
                                                      ▼
                                                   [DevOps]
                                                      │
                                                      ▼
                                                     END
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from .state import AgentState
from .nodes import (
    # Phase 1: Planning
    ba_node,
    po_node,
    architect_node,
    planning_evaluator_node,
    # HITL Gates
    hitl_gate1_node,
    hitl_gate2_node,
    # Phase 2: Building (parallel)
    backend_builder_node,
    frontend_builder_node,
    qa_node,
    # Integration Validation
    integration_validator_node,
    # Phase 3: DevOps
    devops_node,
    # Conditional edges
    should_continue_planning,
    should_fix_or_continue,
)


def fan_out_to_builders(state: AgentState) -> list[Send]:
    """
    Fan-out: dispatch to Backend and Frontend builders in parallel.
    
    Each builder receives the full state but only reads its own spec
    (backend_spec / frontend_spec). The merge_files reducer on
    generated_files handles combining results by path.
    
    This is the LangChain 'Send' pattern for parallel subagent invocation.
    """
    return [
        Send("backend_builder", state),
        Send("frontend_builder", state),
    ]


def fix_fan_out_to_builders(state: AgentState) -> list[Send]:
    """
    Fan-out for fix cycle: same as fan_out_to_builders but used
    after integration_validator to avoid triggering HITL interrupt.
    """
    return [
        Send("backend_builder", state),
        Send("frontend_builder", state),
    ]


def create_workflow() -> StateGraph:
    """
    Creates the full AI Dev Team workflow graph with parallel builders.
    """

    workflow = StateGraph(AgentState)

    # =========================================================================
    # ADD NODES
    # =========================================================================

    # Phase 1: Planning (sequential cycle)
    workflow.add_node("ba_node", ba_node)
    workflow.add_node("po_node", po_node)
    workflow.add_node("architect_node", architect_node)
    workflow.add_node("planning_evaluator", planning_evaluator_node)

    # HITL Gates
    workflow.add_node("hitl_gate_1", hitl_gate1_node)
    workflow.add_node("hitl_gate_2", hitl_gate2_node)

    # Phase 2: Building (parallel-ready)
    workflow.add_node("backend_builder", backend_builder_node)
    workflow.add_node("frontend_builder", frontend_builder_node)
    workflow.add_node("qa_agent", qa_node)

    # Fix dispatcher — a passthrough node that fans out to builders during fix cycles
    async def fix_dispatcher(state: AgentState) -> dict:
        """Passthrough node that exists to fan-out to parallel builders during fix cycle."""
        print(f"\n  🔄 Fix dispatcher: re-launching parallel builders...")
        return {}

    workflow.add_node("fix_dispatcher", fix_dispatcher)

    # Integration Validation
    workflow.add_node("integration_validator", integration_validator_node)

    # Phase 3: DevOps
    workflow.add_node("devops_agent", devops_node)

    # =========================================================================
    # ADD EDGES
    # =========================================================================

    # Entry point
    workflow.set_entry_point("ba_node")

    # Phase 1: Planning cycle
    workflow.add_edge("ba_node", "po_node")
    workflow.add_edge("po_node", "architect_node")
    workflow.add_edge("architect_node", "planning_evaluator")

    # Evaluator decides: converged → HITL, or loop
    workflow.add_conditional_edges(
        "planning_evaluator",
        should_continue_planning,
        {
            "hitl_gate_1": "hitl_gate_1",
            "ba_node": "ba_node",
        }
    )

    # HITL Gate 1 → Fan-out to parallel builders
    workflow.add_conditional_edges(
        "hitl_gate_1",
        fan_out_to_builders,
        ["backend_builder", "frontend_builder"],
    )

    # Both builders → QA (LangGraph waits for both to complete before proceeding)
    workflow.add_edge("backend_builder", "qa_agent")
    workflow.add_edge("frontend_builder", "qa_agent")

    # QA → Integration Validator
    workflow.add_edge("qa_agent", "integration_validator")

    # Integration Validator: valid → HITL 2, fix → fix_dispatcher → parallel rebuild
    workflow.add_conditional_edges(
        "integration_validator",
        should_fix_or_continue,
        {
            "hitl_gate_2": "hitl_gate_2",
            "fan_out_builders": "fix_dispatcher",
        }
    )

    # Fix dispatcher fans out to parallel builders
    workflow.add_conditional_edges(
        "fix_dispatcher",
        fix_fan_out_to_builders,
        ["backend_builder", "frontend_builder"],
    )

    # HITL Gate 2 → DevOps
    workflow.add_edge("hitl_gate_2", "devops_agent")

    # DevOps → END
    workflow.add_edge("devops_agent", END)

    return workflow


def compile_workflow(checkpointer=None):
    """Compile the workflow with checkpointer for persistence and HITL interrupts."""
    workflow = create_workflow()

    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_gate_1", "hitl_gate_2"],
    )

    return compiled
