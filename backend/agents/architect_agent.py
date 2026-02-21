"""
Architect Agent

Designs the full technical architecture. Produces:
- Tech spec with project structure, data models, API endpoints, DB schema
- Separate specs for backend_builder, frontend_builder, qa_agent, devops_agent
- ER and sequence diagrams in Mermaid
"""

import json
from ..graph.state import AgentState, TechSpec
from ..services import call_llm


# ---------------------------------------------------------------------------
# STEP 1: Main tech spec
# ---------------------------------------------------------------------------

TECH_SPEC_PROMPT = """Eres un Arquitecto de Software senior. Disenas la arquitectura tecnica completa de un sistema a partir de requerimientos e historias de usuario.

STACK OBLIGATORIO (no cambiar):
- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.x (sync session) + SQLite (archivo local)
- Frontend: React 18 + Vite 5 + TailwindCSS 3 + React Router v6 + Axios + Recharts
- ML: scikit-learn TF-IDF + Naive Bayes (MultinomialNB). Modelo entrenado con datos sinteticos generados en un script train.py. Serializado con joblib a ml/models/classifier.joblib. Se entrena durante docker build (RUN python ml/train.py). La app carga el .joblib al arrancar. Dependencias: scikit-learn, joblib.
- GenAI: SDK anthropic (AsyncAnthropic). API key por env var ANTHROPIC_API_KEY. Modelo: claude-sonnet-4-20250514. Si ANTHROPIC_API_KEY no esta configurada, el servicio devuelve un fallback dummy (texto placeholder) en vez de crashear.
- Auth: Simple/dummy — tabla users en SQLite con email + hashed_password (passlib bcrypt). Login devuelve un token random (uuid4) guardado en tabla sessions. Middleware valida token contra la tabla. SIN JWT, SIN python-jose, SIN SECRET_KEY para tokens.
- BD: SQLite archivo local (data.db). Se crea automaticamente al arrancar. SIN PostgreSQL, SIN asyncpg, SIN servidor de BD externo.
- DB migrations: NO usar Alembic. Crear tablas con SQLAlchemy metadata.create_all() en el lifespan de FastAPI.
- Infra: Docker Compose / Podman Compose (compatible ambos). nginx como reverse proxy del frontend.
- Tests: pytest + httpx.AsyncClient + unittest.mock
ESTRUCTURA DE ARCHIVOS OBLIGATORIA:
El proyecto se despliega con docker-compose / podman-compose. La raiz contiene:

backend/                  -> contexto Docker del backend
  core/config.py          -> Settings con pydantic-settings (ANTHROPIC_API_KEY, DB path)
  database.py             -> create_engine SQLite, SessionLocal, get_db dependency
  models.py               -> Modelos SQLAlchemy (Base, todas las tablas, User con email+hashed_password, Session con token)
  schemas.py              -> Schemas Pydantic para request/response
  auth.py                 -> Login: verificar password, crear session token (uuid4), guardar en tabla sessions. get_current_user: leer token de header, buscar en sessions.
  main.py                 -> FastAPI app, include routers, CORS, lifespan (Base.metadata.create_all + seed data)
  routers/                -> Un archivo por recurso: auth_router.py, {recurso}_router.py, dashboard_router.py
  services/               -> ml_service.py (carga modelo .joblib y clasifica), genai_service.py (Anthropic con fallback si no hay API key)
  ml/train.py             -> Script que genera datos sinteticos y entrena TF-IDF + MultinomialNB. Guarda en ml/models/classifier.joblib
  ml/predict.py           -> Carga classifier.joblib, expone classify(text) -> {"category": str, "confidence": float}
  ml/models/              -> Carpeta donde se guarda classifier.joblib (generado por train.py)
  requirements.txt        -> fastapi, uvicorn[standard], sqlalchemy, aiosqlite, anthropic, passlib[bcrypt], pydantic-settings, python-multipart, scikit-learn, joblib
  Dockerfile
  tests/                  -> conftest.py + test_*.py
frontend/                 -> contexto Docker del frontend
  package.json            -> react, react-dom, react-router-dom, axios, recharts, tailwindcss, autoprefixer, postcss
  vite.config.js          -> proxy /api a backend:8000
  tailwind.config.js
  postcss.config.js
  index.html
  src/main.jsx
  src/index.css           -> @tailwind base/components/utilities
  src/App.jsx             -> Routes, layout, navigation
  src/services/api.js     -> Instancia axios con baseURL /api, interceptor token
  src/pages/              -> LoginPage.jsx, DashboardPage.jsx, etc.
  src/components/         -> Componentes reutilizables
  Dockerfile              -> node:18-alpine build + nginx:alpine. USAR npm install (NO npm ci).
  nginx-site.conf
docker-compose.yml        -> Solo 2 servicios: backend + frontend. SIN postgres (usamos SQLite).
.env.example
README.md

REGLAS DE IMPORTS BACKEND (CRITICO):
- from core.config import settings
- from database import SessionLocal, get_db
- from models import User, Session, {Modelo}
- from schemas import {Schema}Create, {Schema}Response
- from auth import get_current_user, create_session_token
- from services.ml_service import classify_{dominio}  (ml_service carga el modelo .joblib internamente)
- from services.genai_service import generate_{accion}  (genai_service tiene fallback si no hay API key)
- NUNCA: from app.xxx, from backend.xxx (no son paquetes Python)

REGLAS CRITICAS PARA MERMAID (sintaxis estricta):
- erDiagram: tipos de atributos SOLO: int, string, float, boolean, datetime. NUNCA usar "FK", "UK", "PK" como tipo — van como sufijo separado: "int id PK", "int user_id FK". Un atributo por linea. Sin comas.
- sequenceDiagram: usar actor para usuarios, participant para servicios. Flechas: ->>, -->>, -x. Sin parentesis en labels.
- NO incluir caracteres especiales, acentos ni espacios en nombres de entidades/participantes.
- Cada diagrama debe ser valido para mermaid v10.

 Para CADA archivo incluye:
- path: ruta relativa desde la raiz del proyecto
- description: que hace
- instruction: instruccion DETALLADA para el builder (que clases, funciones, imports, logica)
- domain: "backend" | "frontend" | "devops"
- depends_on: lista de paths de archivos que este importa

RESPONDE UNICAMENTE con JSON valido (sin markdown):
{
  "tech_spec": {
    "project_structure": {
      "files": [
        {"path": "backend/core/config.py", "description": "...", "instruction": "...", "domain": "backend", "depends_on": []},
        {"path": "backend/database.py", "description": "...", "instruction": "...", "domain": "backend", "depends_on": ["backend/core/config.py"]}
      ]
    },
    "data_models": [
      {"name": "User", "table": "users", "fields": [{"name": "id", "type": "Integer", "pk": true}, {"name": "email", "type": "String(255)", "unique": true}], "relationships": []}
    ],
    "api_endpoints": [
      {"method": "POST", "path": "/api/auth/login", "description": "Login", "request_schema": "LoginRequest", "response_schema": "TokenResponse", "auth_required": false, "us_ids": ["US-001"]}
    ],
    "db_schema": "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, ...);",
    "ml_pipeline": {"type": "tfidf_naive_bayes", "library": "scikit-learn", "serialization": "joblib", "model_path": "ml/models/classifier.joblib", "train_script": "ml/train.py", "predict_module": "ml/predict.py", "input": "texto libre", "output": "categoria + confianza (0-1)", "categories": ["cat1", "cat2", "cat3"], "training_data": "sintetico (generado en train.py, 50-100 ejemplos por categoria)", "description": "..."},
    "genai_integration": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "fallback_if_no_key": true, "use_cases": [{"name": "...", "prompt_template": "...", "input": "...", "output": "..."}]},
    "mermaid_er": "erDiagram\\n    USER ||--o{ INCIDENT : creates\\n    USER { int id PK\\n string email\\n string hashed_password }\\n    INCIDENT { int id PK\\n string title\\n int user_id FK }",
    "mermaid_sequence": [{"title": "Flujo principal", "code": "sequenceDiagram\\n    actor User\\n    User->>Frontend: accion\\n    Frontend->>Backend: POST /api/recurso\\n    Backend-->>Frontend: 200 OK"}],
    "stack": {"backend": "FastAPI+SQLAlchemy+Python3.11", "frontend": "React18+Vite+TailwindCSS", "db": "SQLite", "ml": "scikit-learn TF-IDF+NaiveBayes (joblib)", "genai": "Anthropic Claude (con fallback)"}
  },
  "feasibility": "approved",
  "reasoning": "Explicacion de decisiones"
}"""

# ---------------------------------------------------------------------------
# STEP 2: Builder-specific specs
# ---------------------------------------------------------------------------

BUILDER_SPEC_PROMPT = """Eres el Arquitecto. A partir de la tech spec ya generada, produce specs separadas para cada equipo builder.

Cada spec es un subconjunto enfocado de la tech spec, con instrucciones adicionales especificas para ese builder.

RESPONDE UNICAMENTE con JSON valido:
{
  "backend_spec": {
    "files": [lista de file specs del dominio backend, copiados de project_structure.files donde domain=="backend"],
    "import_rules": "Reglas de imports entre archivos backend (from models import X, from database import Y, etc.)",
    "db_schema": "SQL completo de CREATE TABLE (SQLite syntax: INTEGER PRIMARY KEY AUTOINCREMENT, TEXT, etc.)",
    "api_endpoints": [endpoints],
    "ml_pipeline": {...incluyendo train_script, predict_module, model_path, categories, training_data sintetico},
    "genai_integration": {...incluyendo fallback_if_no_key: true}
  },
  "frontend_spec": {
    "files": [lista de file specs del dominio frontend],
    "api_base_url": "/api",
    "api_endpoints": [endpoints para que el frontend sepa que llamar],
    "auth_flow": "Token simple en localStorage, header Authorization: Bearer {token}, redirect a /login si 401"
  },
  "qa_spec": {
    "test_files": [
      {"path": "backend/tests/conftest.py", "instruction": "Fixtures: TestClient sync, BD SQLite en memoria, usuario test, token valido", "focus_us": []},
      {"path": "backend/tests/test_auth.py", "instruction": "Tests: login ok, login invalido 401, acceso sin token 401", "focus_us": ["US-xxx"]}
    ],
    "coverage_targets": "Todos los endpoints, servicios ML y GenAI (mockeado)"
  },
  "devops_spec": {
    "files": [lista de file specs del dominio devops],
    "docker_notes": "backend Dockerfile: python:3.11-slim, SIN HEALTHCHECK. INCLUIR 'RUN python ml/train.py' despues de COPY para entrenar el modelo ML durante el build. frontend Dockerfile: node:18-alpine build (npm install, NO npm ci) + nginx:alpine. docker-compose: solo backend+frontend, SIN postgres.",
    "env_vars": ["ANTHROPIC_API_KEY"]
  }
}"""


def _build_tech_spec_prompt(state: AgentState) -> str:
    reqs = json.dumps(state["requirements"], indent=2, ensure_ascii=False)
    stories = json.dumps(state["user_stories"], indent=2, ensure_ascii=False)
    inception = json.dumps(state.get("inception"), indent=2, ensure_ascii=False)
    feedback = state.get("planning_feedback", "")
    iteration = state.get("planning_iteration", 0)

    prompt = f"""BRIEF ORIGINAL:
\"\"\"{state['brief']}\"\"\"

REQUERIMIENTOS:
{reqs}

INCEPTION/MVP:
{inception}

HISTORIAS DE USUARIO:
{stories}
"""
    if iteration > 0 and feedback:
        prompt += f"""
FEEDBACK DE ITERACION ANTERIOR:
\"\"\"{feedback}\"\"\"
"""

    prompt += "\nDisena la arquitectura tecnica completa en JSON."
    return prompt


def _build_builder_spec_prompt(tech_spec: dict, state: AgentState) -> str:
    return f"""TECH SPEC YA GENERADA:
{json.dumps(tech_spec, indent=2, ensure_ascii=False)}

BRIEF:
\"\"\"{state['brief'][:500]}\"\"\"

Genera las specs separadas para backend_builder, frontend_builder, qa_agent y devops_agent en JSON."""


async def run_architect_agent(state: AgentState) -> dict:
    requirements = state["requirements"]
    user_stories = state["user_stories"]
    iteration = state.get("planning_iteration", 0)

    print(f"  🏗️  Designing architecture for {len(user_stories)} user stories...")

    # --- CALL 1: Main tech spec ---
    print(f"  🏗️  [1/2] Generating main tech spec...")
    result = await call_llm(
        system_prompt=TECH_SPEC_PROMPT,
        user_prompt=_build_tech_spec_prompt(state),
        temperature=0.2,
        max_tokens=50_000,
        agent="architect_agent",
    )

    if isinstance(result, list):
        result = result[0] if result and isinstance(result[0], dict) else {"error": "LLM returned list"}

    if not isinstance(result, dict) or "error" in result:
        print(f"  ⚠️  LLM error: {result.get('error') if isinstance(result, dict) else result}")
        return _fallback(state)

    raw_spec = result.get("tech_spec", {})

    tech_spec = TechSpec(
        project_structure=raw_spec.get("project_structure", {}),
        data_models=raw_spec.get("data_models", []),
        api_endpoints=raw_spec.get("api_endpoints", []),
        db_schema=raw_spec.get("db_schema", ""),
        ml_pipeline=raw_spec.get("ml_pipeline", {}),
        genai_integration=raw_spec.get("genai_integration", {}),
        mermaid_er=raw_spec.get("mermaid_er", ""),
        mermaid_sequence=raw_spec.get("mermaid_sequence", []),
        stack=raw_spec.get("stack", {
            "backend": "FastAPI+SQLAlchemy+Python3.11",
            "frontend": "React18+Vite+TailwindCSS",
            "db": "PostgreSQL15",
            "ml": "keyword-classifier",
            "genai": "Anthropic Claude",
        }),
        created_by="Architect Agent",
        iteration=iteration,
    )

    # --- CALL 2: Builder-specific specs ---
    print(f"  🏗️  [2/2] Generating builder-specific specs...")
    builder_result = await call_llm(
        system_prompt=BUILDER_SPEC_PROMPT,
        user_prompt=_build_builder_spec_prompt(raw_spec, state),
        temperature=0.2,
        max_tokens=50_000,
        agent="architect_agent",
    )

    if isinstance(builder_result, list):
        builder_result = builder_result[0] if builder_result and isinstance(builder_result[0], dict) else {}

    backend_spec = builder_result.get("backend_spec") if isinstance(builder_result, dict) else None
    frontend_spec = builder_result.get("frontend_spec") if isinstance(builder_result, dict) else None
    qa_spec = builder_result.get("qa_spec") if isinstance(builder_result, dict) else None
    devops_spec = builder_result.get("devops_spec") if isinstance(builder_result, dict) else None

    # Diagrams
    er_svg = _mermaid_to_svg_placeholder(tech_spec["mermaid_er"], "ER Diagram")
    seq_svgs = [
        {"title": seq["title"], "svg": _mermaid_to_svg_placeholder(seq["code"], seq["title"])}
        for seq in tech_spec.get("mermaid_sequence", [])
    ]

    feasibility = result.get("feasibility", "approved")

    print(f"  ✅ Architecture designed")
    print(f"     Files: {len(raw_spec.get('project_structure', {}).get('files', []))}")
    print(f"     Data models: {len(tech_spec['data_models'])}")
    print(f"     API endpoints: {len(tech_spec['api_endpoints'])}")
    print(f"     Builder specs: backend={'yes' if backend_spec else 'no'} frontend={'yes' if frontend_spec else 'no'} qa={'yes' if qa_spec else 'no'} devops={'yes' if devops_spec else 'no'}")

    return {
        "tech_spec": tech_spec,
        "backend_spec": backend_spec,
        "frontend_spec": frontend_spec,
        "qa_spec": qa_spec,
        "devops_spec": devops_spec,
        "er_diagram_svg": er_svg,
        "sequence_diagrams_svg": seq_svgs,
        "feasibility": feasibility,
        "reasoning": result.get("reasoning", "Architecture designed."),
    }


def _mermaid_to_svg_placeholder(mermaid_code: str, title: str) -> str:
    escaped = mermaid_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#f8f9fa" rx="8"/>
  <text x="400" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">{title}</text>
  <text x="20" y="60" font-family="monospace" font-size="11" fill="#555">
    <tspan x="20" dy="0">Mermaid source (render with mermaid.js):</tspan>
    {"".join(f'<tspan x="20" dy="16">{line}</tspan>' for line in escaped.split(chr(10))[:30])}
  </text>
</svg>"""


def _fallback(state):
    return {
        "tech_spec": TechSpec(
            project_structure={}, data_models=[], api_endpoints=[],
            db_schema="", ml_pipeline={}, genai_integration={},
            mermaid_er="", mermaid_sequence=[], stack={},
            created_by="Architect Agent (fallback)", iteration=state.get("planning_iteration", 0),
        ),
        "backend_spec": None,
        "frontend_spec": None,
        "qa_spec": None,
        "devops_spec": None,
        "er_diagram_svg": "<svg/>",
        "sequence_diagrams_svg": [],
        "feasibility": "needs_changes",
        "reasoning": "Fallback: LLM call failed.",
    }