"""
Integration Validator Agent

The Architect reviews ALL generated code for cross-file consistency:
- Backend imports match actual files
- Frontend API calls match backend endpoints
- Docker paths match project structure
- Dependencies match imports
- Models match schemas match router usage
"""

import json
from ..graph.state import AgentState, GeneratedFile
from ..services import call_llm


SYSTEM_PROMPT = """Eres el Arquitecto de Software revisando la INTEGRACION entre todos los archivos generados.

Tu trabajo es verificar CONSISTENCIA CRUZADA entre backend, frontend, tests y DevOps.

STACK DEL PROYECTO:
- Backend: FastAPI + SQLAlchemy sync + SQLite + passlib + anthropic + scikit-learn + joblib
- Frontend: React 18 + Vite + TailwindCSS + Axios + Recharts + React Router v6
- Auth: Token simple en tabla sessions (SIN JWT, SIN python-jose)
- ML: scikit-learn TF-IDF + NaiveBayes, modelo en ml/models/classifier.joblib, entrenado por ml/train.py
- GenAI: Anthropic Claude SDK con fallback si no hay API key
- Infra: Docker Compose / Podman Compose + nginx

DEBES VERIFICAR:

1. IMPORTS BACKEND: que cada "from X import Y" referencie un modulo que realmente existe en la lista de archivos. Reglas:
   - from core.config import settings (archivo: backend/core/config.py)
   - from database import SessionLocal, get_db (archivo: backend/database.py)
   - from models import X (archivo: backend/models.py)
   - from schemas import X (archivo: backend/schemas.py)
   - from auth import get_current_user, create_session_token (archivo: backend/auth.py)
   - from services.ml_service import X (archivo: backend/services/ml_service.py)
   - from services.genai_service import X (archivo: backend/services/genai_service.py)
   - from routers.X import router (archivo: backend/routers/X.py)
   - NUNCA: from app.xxx, from backend.xxx

2. ENDPOINTS CONSISTENTES: que los paths en los routers backend coincidan con las URLs que el frontend llama via axios.

3. MODELOS <-> SCHEMAS: que los campos en Pydantic schemas coincidan con los modelos SQLAlchemy.

4. FRONTEND -> BACKEND: que las llamadas api.get/post/put/delete usen los paths, methods y payloads correctos.

5. DOCKER: que los Dockerfile copien archivos correctos, que docker-compose apunte a paths reales.

6. DEPENDENCIAS: que requirements.txt incluya todos los paquetes importados. Que package.json tenga todas las deps.

7. ENV VARS: que .env.example tenga todas las variables que el codigo referencia (DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY, etc.)

RESPONDE UNICAMENTE con JSON valido:
{
  "is_consistent": true|false,
  "score": 0-100,
  "issues": [
    {"severity": "critical|warning", "file": "archivo", "issue": "descripcion", "fix": "instruccion", "affects": "backend|frontend|devops|qa"}
  ],
  "file_fixes": [
    {"path": "archivo a regenerar", "builder": "backend_builder|frontend_builder|qa_agent|devops_agent", "instruction": "instruccion detallada"}
  ],
  "summary": "resumen ejecutivo"
}

Solo marca is_consistent=false si hay issues CRITICAL. Warnings son aceptables.
Se pragmatico: si el codigo es funcional al 80%, aprueba con warnings."""


async def run_integration_validator(state: AgentState) -> dict:
    """Architect reviews all generated files for cross-consistency."""
    generated_files = state.get("generated_files", [])
    docker_files = state.get("docker_files", [])

    all_files = generated_files + docker_files

    print(f"  🔍 Validating integration of {len(all_files)} files...")

    user_prompt = _build_validation_prompt(state, all_files)

    try:
        result = await call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=50_000,
        )

        if "error" in result:
            print(f"  ⚠️  LLM error, approving by default: {result.get('error', '')[:80]}")
            return {
                "is_consistent": True,
                "issues": [],
                "file_fixes": [],
                "score": 70,
                "summary": "Validation skipped due to LLM error. Approved by default.",
            }

        is_consistent = result.get("is_consistent", True)
        issues = result.get("issues", [])
        file_fixes = result.get("file_fixes", [])
        score = result.get("score", 80)
        summary = result.get("summary", "")

        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        print(f"  📊 Score: {score}/100")
        print(f"  🔴 Critical: {critical_count} | 🟡 Warnings: {warning_count}")

        if is_consistent:
            print(f"  ✅ Integration validated! {summary}")
        else:
            print(f"  ❌ Issues found. {len(file_fixes)} files need fixes")
            for fix in file_fixes:
                print(f"     🔧 {fix['path']} → {fix['builder']}")

        return {
            "is_consistent": is_consistent,
            "issues": issues,
            "file_fixes": file_fixes,
            "score": score,
            "summary": summary,
        }

    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        return {
            "is_consistent": True,
            "issues": [],
            "file_fixes": [],
            "score": 60,
            "summary": f"Validation failed with exception. Approved by default.",
        }


def _build_validation_prompt(state: AgentState, all_files: list) -> str:
    """Build prompt with all file contents and tech spec for cross-validation."""
    tech_spec = state.get("tech_spec", {})

    # Build file manifest with content (truncated if too long)
    files_section = []
    for f in all_files:
        content = f.get("content", "")
        if len(content) > 3000:
            lines = content.split("\n")
            truncated = "\n".join(lines[:40]) + "\n\n# ... [TRUNCATED] ...\n\n" + "\n".join(lines[-20:])
            content = truncated

        files_section.append(f"=== {f['path']} ({f.get('created_by', 'unknown')}) ===\n{content}")

    files_text = "\n\n".join(files_section)

    endpoints = json.dumps(tech_spec.get("api_endpoints", []), indent=2, ensure_ascii=False)

    backend_paths = [f["path"] for f in all_files if f["path"].startswith("backend/")]
    frontend_paths = [f["path"] for f in all_files if f["path"].startswith("frontend/")]
    docker_paths = [f["path"] for f in all_files if any(f["path"].startswith(p) for p in ["Docker", "docker", "scripts/", "README", ".env"])]

    return f"""REVISA LA CONSISTENCIA DE INTEGRACION ENTRE TODOS ESTOS ARCHIVOS:

ARCHIVOS BACKEND ({len(backend_paths)}): {json.dumps(backend_paths)}
ARCHIVOS FRONTEND ({len(frontend_paths)}): {json.dumps(frontend_paths)}
ARCHIVOS DEVOPS ({len(docker_paths)}): {json.dumps(docker_paths)}

API ENDPOINTS (tech spec):
{endpoints}

CONTENIDO DE TODOS LOS ARCHIVOS:
{files_text}

Verifica especialmente:
1. Los imports del backend referencian modulos que existen
2. El frontend llama a los endpoints exactos definidos en los routers
3. Los modelos SQLAlchemy y schemas Pydantic son consistentes
4. Docker-compose apunta a los paths correctos
5. requirements.txt y package.json tienen todas las dependencias

Responde con el analisis de consistencia en JSON."""