"""
BA Agent - Business Analyst

Analyzes any brief and generates structured requirements.
Uses LLM to understand the domain and extract functional/non-functional requirements.
"""

import json
from ..graph.state import AgentState, Requirement
from ..services import call_llm

SYSTEM_PROMPT = """Eres un Business Analyst senior. Analizas briefs de proyectos de software y extraes requerimientos estructurados.

STACK FIJO DEL EQUIPO (tenlo en cuenta al analizar factibilidad):
- Backend: Python 3.11 + FastAPI + SQLAlchemy (sync, SQLite) + aiosqlite
- BD: SQLite (archivo local, CERO configuración, sin servidor de BD)
- Frontend: React 18 + Vite + TailwindCSS + React Router v6 + Axios + Recharts
- Auth: Dummy/simple — tabla users en SQLite, login por email+password con hash bcrypt, sesión por token simple en localStorage. SIN JWT complejo, SIN python-jose, SIN configuración remota.
- ML: scikit-learn TF-IDF + Naive Bayes, modelo entrenado con datos sintéticos, serializado con joblib
- GenAI: Anthropic Claude API vía SDK `anthropic` (API key por env var ANTHROPIC_API_KEY, con fallback si no hay key)
- Infra: Docker Compose / Podman Compose (compatible ambos), nginx reverse proxy
- Tests: pytest + httpx

REGLAS:
1. Analiza el brief completo. Extrae TODOS los requerimientos implícitos y explícitos.
2. Cada requerimiento debe ser atómico (una sola funcionalidad), testeable y claro.
3. Clasifica cada requerimiento por dominio: backend, frontend, ml, genai, data, infra.
4. Asigna prioridad: "must" (MVP esencial), "should" (importante), "could" (nice-to-have).
5. SIEMPRE incluye requerimientos de:
   - CRUD principal del dominio (endpoints REST)
   - Autenticación simple (login por email+password, tabla users en SQLite, token simple)
   - Dashboard con métricas y gráficos (Recharts)
   - Componente ML si el brief lo sugiere (clasificación con modelo entrenado scikit-learn)
   - Componente GenAI si el brief lo sugiere (generación de texto vía Anthropic, con fallback)
   - No funcionales: seguridad, validación, manejo de errores
6. Genera entre 8 y 15 requerimientos.
7. NO propongas tecnologías fuera del stack fijo.

Si recibes feedback de iteración anterior, AJUSTA los requerimientos según el feedback.

RESPONDE ÚNICAMENTE con JSON válido (sin markdown, sin texto extra):
{
  "requirements": [
    {
      "id": "REQ-001",
      "title": "Título conciso",
      "description": "Descripción detallada de qué debe hacer el sistema",
      "type": "functional|non_functional",
      "priority": "must|should|could",
      "domain": "backend|frontend|ml|genai|data|infra"
    }
  ],
  "reasoning": "Explicación breve del análisis"
}"""


def _build_user_prompt(state: AgentState) -> str:
    brief = state["brief"]
    feedback = state.get("planning_feedback", "")
    iteration = state.get("planning_iteration", 0)

    prompt = f"""BRIEF DEL PROYECTO:
\"\"\"
{brief}
\"\"\"
"""
    if iteration > 0 and feedback:
        prompt += f"""
FEEDBACK DE ITERACIÓN ANTERIOR (iteración {iteration}):
\"\"\"
{feedback}
\"\"\"
Ajusta los requerimientos según este feedback.
"""

    prompt += "\nAnaliza el brief y genera los requerimientos estructurados en JSON."
    return prompt


async def run_ba_agent(state: AgentState) -> dict:
    brief = state["brief"]
    feedback = state.get("planning_feedback", "")
    iteration = state.get("planning_iteration", 0)

    print(f"  📝 Analyzing brief: {brief[:80]}...")
    if feedback:
        print(f"  📝 Incorporating feedback: {feedback[:80]}...")

    result = await call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(state),
        temperature=0.3,
        max_tokens=50_000,
        agent="ba_agent",
    )

    if "error" in result:
        print(f"  ⚠️  LLM error: {result.get('error')}")
        return _fallback(state)

    raw_reqs = result.get("requirements", [])
    requirements = []
    for i, req in enumerate(raw_reqs):
        requirements.append(Requirement(
            id=req.get("id", f"REQ-{str(i+1).zfill(3)}"),
            title=req.get("title", f"Requirement {i+1}"),
            description=req.get("description", ""),
            type=req.get("type", "functional"),
            priority=req.get("priority", "should"),
            domain=req.get("domain", "backend"),
            created_by="BA Agent",
            iteration=iteration,
        ))

    print(f"  ✅ Generated {len(requirements)} requirements")
    for req in requirements:
        print(f"     [{req['id']}] {req['title']} ({req['domain']}, {req['priority']})")

    return {
        "requirements": requirements,
        "reasoning": result.get("reasoning", f"Analyzed brief: {len(requirements)} requirements."),
    }


def _fallback(state):
    return {
        "requirements": [Requirement(
            id="REQ-001", title="Core functionality",
            description=f"Implement: {state['brief'][:200]}",
            type="functional", priority="must", domain="backend",
            created_by="BA Agent (fallback)", iteration=state.get("planning_iteration", 0),
        )],
        "reasoning": "Fallback: LLM call failed.",
    }
