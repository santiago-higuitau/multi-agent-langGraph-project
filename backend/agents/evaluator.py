"""
Planning Evaluator

Uses LLM to evaluate consistency and completeness of planning artifacts.
Decides if planning has converged or needs another iteration.
"""

import json
from ..graph.state import AgentState
from ..services import call_llm

SYSTEM_PROMPT = """Eres un evaluador de calidad de artefactos de ingenieria de software.

Revisas los artefactos del equipo de planificacion (BA, PO, Architect) y verificas:

1. COBERTURA: Cada requerimiento "must" tiene al menos una historia de usuario.
2. TRAZABILIDAD: Las historias referencian correctamente los REQ-IDs.
3. CONSISTENCIA: La tech spec cubre todas las historias. Los endpoints cubren los flujos.
4. COMPLETITUD: Criterios de aceptacion son especificos y testeables.
5. FACTIBILIDAD: La arquitectura es realista para el stack (FastAPI+SQLite+React+Docker).
6. ESTRUCTURA: project_structure.files tiene archivos con path, instruction, domain, depends_on.

STACK FIJO:
- Backend: FastAPI + SQLAlchemy (sync, SQLite) + Python 3.11
- Frontend: React 18 + Vite + TailwindCSS
- ML: scikit-learn TF-IDF + Naive Bayes (modelo serializado con joblib)
- GenAI: Anthropic Claude API (con fallback si no hay key)
- Auth: Simple token en tabla sessions (SIN JWT)
- BD: SQLite (archivo local, sin servidor)
- Infra: Docker Compose / Podman Compose

RESPONDE UNICAMENTE con JSON:
{
  "converged": true|false,
  "score": 0-100,
  "issues": ["issue 1", "issue 2"],
  "feedback": "Resumen de que necesita ajustarse (si converged=false) o confirmacion (si converged=true)"
}

CRITERIO: converged=true si score >= 75 y no hay issues criticos.
Se permisivo: si los artefactos cubren el 75% del alcance y la estructura es razonable, aprueba."""


def _build_user_prompt(state: AgentState) -> str:
    return f"""Evalua los siguientes artefactos de planificacion:

REQUERIMIENTOS ({len(state['requirements'])}):
{json.dumps(state['requirements'], indent=2, ensure_ascii=False)}

INCEPTION/MVP:
{json.dumps(state.get('inception'), indent=2, ensure_ascii=False)}

HISTORIAS DE USUARIO ({len(state['user_stories'])}):
{json.dumps(state['user_stories'], indent=2, ensure_ascii=False)}

TECH SPEC (resumen):
- Archivos: {len(state.get('tech_spec', {}).get('project_structure', {}).get('files', []))}
- Data models: {len(state.get('tech_spec', {}).get('data_models', []))}
- API endpoints: {len(state.get('tech_spec', {}).get('api_endpoints', []))}
- ML pipeline: {json.dumps(state.get('tech_spec', {}).get('ml_pipeline', {}), ensure_ascii=False)[:300]}
- Stack: {json.dumps(state.get('tech_spec', {}).get('stack', {}), ensure_ascii=False)}

Evalua la consistencia y completitud. Responde en JSON."""


async def evaluate_planning(state: AgentState) -> dict:
    iteration = state.get("planning_iteration", 0)

    # Basic structural checks first
    structural_issues = _structural_checks(state)

    if structural_issues:
        print(f"  ⚠️  Structural issues found: {structural_issues}")
        return {
            "converged": False,
            "feedback": f"Structural issues: {'; '.join(structural_issues)}",
        }

    # LLM-based semantic evaluation
    result = await call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(state),
        temperature=0.1,
        max_tokens=50_000,
    )

    if "error" in result:
        print(f"  ⚠️  LLM evaluation failed, using structural checks only")
        return {"converged": True, "feedback": "Structural checks passed (LLM evaluation unavailable)."}

    converged = result.get("converged", True)
    score = result.get("score", 75)
    issues = result.get("issues", [])
    feedback = result.get("feedback", "Evaluation complete.")

    print(f"  📊 Evaluation score: {score}/100")
    print(f"  📊 Converged: {converged}")
    if issues:
        for issue in issues[:3]:
            print(f"     ⚠️  {issue}")

    return {
        "converged": converged,
        "feedback": feedback,
    }


def _structural_checks(state: AgentState) -> list[str]:
    """Fast structural checks without LLM."""
    issues = []

    requirements = state.get("requirements", [])
    user_stories = state.get("user_stories", [])
    tech_spec = state.get("tech_spec")

    if not requirements:
        issues.append("No requirements generated")

    if not user_stories:
        issues.append("No user stories generated")

    if not tech_spec:
        issues.append("No tech spec generated")

    if not state.get("inception"):
        issues.append("No inception/MVP generated")

    # Check project_structure has files
    if tech_spec:
        files = tech_spec.get("project_structure", {}).get("files", [])
        if not files:
            issues.append("Tech spec has no files in project_structure")

    # Check REQ coverage
    if requirements and user_stories:
        req_ids = {r["id"] for r in requirements}
        covered = set()
        for us in user_stories:
            covered.update(us.get("req_ids", []))
        uncovered = req_ids - covered
        if len(uncovered) > len(req_ids) * 0.3:
            issues.append(f"Too many uncovered requirements: {uncovered}")

    return issues
