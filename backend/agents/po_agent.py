"""
Product Owner Agent

Receives requirements from BA, defines MVP scope, risks, and generates
user stories with acceptance criteria.
"""

import json
from ..graph.state import AgentState, InceptionItem, UserStory
from ..services import call_llm

SYSTEM_PROMPT = """Eres un Product Owner senior experto en desarrollo ágil.

Recibes requerimientos de un Business Analyst y debes:
1. Definir el alcance del MVP (qué entra y qué no)
2. Identificar riesgos concretos del proyecto con mitigaciones
3. Generar historias de usuario con criterios de aceptación detallados

STACK FIJO (para que las historias sean realistas):
- Backend: Python 3.11 + FastAPI + SQLAlchemy (sync, SQLite) + aiosqlite
- BD: SQLite (archivo local, sin servidor, sin configuración)
- Frontend: React 18 + Vite + TailwindCSS + Axios + Recharts
- Auth: Dummy/simple — tabla users en SQLite, login email+password, token simple en localStorage. SIN JWT complejo.
- ML: scikit-learn TF-IDF + Naive Bayes, modelo serializado con joblib
- GenAI: Anthropic Claude API (SDK anthropic, key por env var, con fallback dummy)
- Infra: Docker Compose / Podman Compose, nginx
- Tests: pytest + httpx

REGLAS:
1. El MVP incluye TODOS los "must" y los "should" más importantes.
2. Formato historia: "Como [rol], quiero [acción], para [beneficio]".
3. Criterios de aceptación en formato Given/When/Then, específicos y testeables.
4. Cada historia DEBE referenciar los REQ-IDs que implementa (trazabilidad).
5. Story points: 1, 2, 3, 5, 8 según complejidad real.
6. Dominio por historia: backend, frontend, ml, genai, data.
7. Genera entre 6 y 12 historias de usuario.
8. Riesgos específicos al proyecto, no genéricos.
9. Métricas de éxito medibles y concretas.
10. NO propongas tecnologías fuera del stack fijo.

RESPONDE ÚNICAMENTE con JSON válido (sin markdown):
{
  "inception": {
    "id": "INC-001",
    "mvp_scope": ["REQ-001", "REQ-002"],
    "out_of_scope": ["REQ-010"],
    "risks": [
      {"id": "RISK-001", "description": "...", "mitigation": "...", "severity": "high|medium|low"}
    ],
    "success_metrics": ["Métrica medible 1"],
    "tech_constraints": ["Restricción técnica 1"]
  },
  "user_stories": [
    {
      "id": "US-001",
      "title": "Título conciso",
      "description": "Como [rol], quiero [acción], para [beneficio]",
      "acceptance_criteria": [
        "GIVEN contexto WHEN acción THEN resultado esperado"
      ],
      "req_ids": ["REQ-001"],
      "domain": "backend|frontend|ml|genai|data",
      "priority": "must|should|could",
      "story_points": 3
    }
  ],
  "reasoning": "Explicación de decisiones de priorización"
}"""


def _build_user_prompt(state: AgentState) -> str:
    reqs = state["requirements"]
    feedback = state.get("planning_feedback", "")
    iteration = state.get("planning_iteration", 0)

    reqs_text = json.dumps(reqs, indent=2, ensure_ascii=False)

    prompt = f"""BRIEF ORIGINAL:
\"\"\"{state['brief']}\"\"\"

REQUERIMIENTOS DEL BA:
{reqs_text}
"""
    if iteration > 0 and feedback:
        prompt += f"""
FEEDBACK DE ITERACIÓN ANTERIOR:
\"\"\"{feedback}\"\"\"
Ajusta el MVP y las historias según este feedback.
"""

    prompt += "\nDefine el MVP, riesgos e historias de usuario en JSON."
    return prompt


async def run_po_agent(state: AgentState) -> dict:
    requirements = state["requirements"]
    iteration = state.get("planning_iteration", 0)

    print(f"  📋 Processing {len(requirements)} requirements into MVP + stories...")

    result = await call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(state),
        temperature=0.3,
        max_tokens=50_000,
    )

    if "error" in result:
        print(f"  ⚠️  LLM error: {result.get('error')}")
        return _fallback(state)

    # Parse inception
    raw_inc = result.get("inception", {})
    inception = InceptionItem(
        id=raw_inc.get("id", "INC-001"),
        mvp_scope=raw_inc.get("mvp_scope", [r["id"] for r in requirements if r["priority"] == "must"]),
        out_of_scope=raw_inc.get("out_of_scope", []),
        risks=raw_inc.get("risks", []),
        success_metrics=raw_inc.get("success_metrics", []),
        tech_constraints=raw_inc.get("tech_constraints", []),
        created_by="Product Owner Agent",
        iteration=iteration,
    )

    # Parse user stories
    raw_stories = result.get("user_stories", [])
    user_stories = []
    for i, us in enumerate(raw_stories):
        user_stories.append(UserStory(
            id=us.get("id", f"US-{str(i+1).zfill(3)}"),
            title=us.get("title", f"Story {i+1}"),
            description=us.get("description", ""),
            acceptance_criteria=us.get("acceptance_criteria", []),
            req_ids=us.get("req_ids", []),
            domain=us.get("domain", "backend"),
            priority=us.get("priority", "should"),
            story_points=us.get("story_points", 3),
            created_by="Product Owner Agent",
            iteration=iteration,
        ))

    print(f"  ✅ MVP defined: {len(inception['mvp_scope'])} in-scope, {len(inception['out_of_scope'])} out")
    print(f"  ✅ Generated {len(user_stories)} user stories")
    for us in user_stories:
        print(f"     [{us['id']}] {us['title']} → {us['req_ids']} ({us['domain']}, {us['story_points']}pts)")

    return {
        "inception": inception,
        "user_stories": user_stories,
        "reasoning": result.get("reasoning", f"MVP + {len(user_stories)} stories defined."),
    }


def _fallback(state):
    reqs = state["requirements"]
    return {
        "inception": InceptionItem(
            id="INC-001", mvp_scope=[r["id"] for r in reqs if r["priority"] == "must"],
            out_of_scope=[], risks=[], success_metrics=[], tech_constraints=[],
            created_by="PO Agent (fallback)", iteration=state.get("planning_iteration", 0),
        ),
        "user_stories": [UserStory(
            id=f"US-{str(i+1).zfill(3)}", title=f"Story for {r['title']}",
            description=f"Como usuario, quiero {r['title'].lower()}", acceptance_criteria=[],
            req_ids=[r["id"]], domain=r["domain"], priority=r["priority"],
            story_points=3, created_by="PO Agent (fallback)", iteration=state.get("planning_iteration", 0),
        ) for i, r in enumerate(reqs)],
        "reasoning": "Fallback: LLM call failed.",
    }
