"""
Backend Builder Agent

Reads file specs from Architect's backend_spec (or tech_spec fallback).
Generates each backend file individually via LLM.
Designed for parallel execution with frontend_builder.
"""

import json
from ..graph.state import AgentState, GeneratedFile
from ..services import call_llm


SYSTEM_PROMPT = """Eres un desarrollador backend senior experto en FastAPI, SQLAlchemy async y Python 3.11.

Genera UNICAMENTE el codigo del archivo que se te pide. El codigo debe ser:
1. COMPLETO y funcional (no placeholders, no TODOs, no "pass")
2. Type hints en todas las funciones
3. Imports correctos segun las reglas del proyecto
4. Docstrings en funciones publicas
5. Manejo de errores con HTTPException y try/except donde aplique

STACK:
- FastAPI + SQLAlchemy 2.x (sync session) + SQLite (archivo local data.db)
- Auth: passlib[bcrypt] para hash passwords, token simple (uuid4) en tabla sessions. SIN JWT, SIN python-jose.
- Config: pydantic-settings (class Settings(BaseSettings))
- GenAI: anthropic SDK (AsyncAnthropic, ANTHROPIC_API_KEY por env var). Si no hay API key, el servicio devuelve texto placeholder en vez de crashear.
- ML: scikit-learn TF-IDF + MultinomialNB. Modelo entrenado con datos sinteticos en ml/train.py, serializado con joblib a ml/models/classifier.joblib. ml/predict.py carga el modelo y expone classify(text). ml_service.py importa de ml/predict.py.

REGLAS CRITICAS DE IMPORTS:
- from core.config import settings
- from database import SessionLocal, get_db
- from models import User, Session, {Modelo}
- from schemas import {Schema}Create, {Schema}Response, {Schema}Update
- from auth import get_current_user, create_session_token
- from services.ml_service import classify_{dominio}  (ml_service importa de ml/predict.py internamente)
- from services.genai_service import generate_{accion}  (tiene fallback si no hay ANTHROPIC_API_KEY)
- NUNCA usar: from app.xxx, from backend.xxx, from src.xxx

REGLAS DE CODIGO:
- SQLAlchemy: usar mapped_column(), Mapped[], relationship(). Base = declarative_base() o DeclarativeBase.
- Database: SQLite con engine sync. SessionLocal = sessionmaker(bind=engine). get_db yield session.
- FastAPI: usar Depends(get_db) para sesion, Depends(get_current_user) para auth.
- Funciones de router: def (sync), NO async def (SQLite sync).
- Pydantic schemas: usar model_config = ConfigDict(from_attributes=True) en lugar de class Config.
- requirements.txt: una dependencia por linea, sin versiones fijas (solo nombre del paquete). NO incluir asyncpg, python-jose, psycopg2. INCLUIR scikit-learn y joblib.

RESPONDE UNICAMENTE con JSON valido (sin markdown):
{
    "content": "codigo python completo del archivo",
    "description": "que hace este archivo en una linea"
}"""


def _get_file_specs(state: AgentState) -> list:
    """Extract backend file specs from architect's backend_spec or project_structure."""
    backend_spec = state.get("backend_spec")
    if backend_spec and isinstance(backend_spec, dict):
        files = backend_spec.get("files", [])
        if files:
            return files

    tech_spec = state.get("tech_spec", {})
    project_structure = tech_spec.get("project_structure", {})

    files = project_structure.get("files", [])
    if isinstance(files, list) and len(files) > 0:
        return [f for f in files if f.get("domain") == "backend"]

    # Legacy format
    specs = []
    backend_structure = project_structure.get("backend/", project_structure.get("backend", {}))
    if isinstance(backend_structure, dict):
        for filename, description in backend_structure.items():
            if isinstance(description, str):
                specs.append({"path": f"backend/{filename}", "description": description, "instruction": description, "depends_on": []})
            elif isinstance(description, dict):
                for sub_file, sub_desc in description.items():
                    path_prefix = filename if filename.endswith("/") else f"{filename}/"
                    specs.append({"path": f"backend/{path_prefix}{sub_file}", "description": str(sub_desc), "instruction": str(sub_desc), "depends_on": []})

    return specs


async def run_backend_builder(state: AgentState, fix_instructions: list = None) -> dict:
    """Generate backend files one by one from tech spec."""
    user_stories = [us for us in state["user_stories"]
                    if us.get("domain") in ("backend", "ml", "genai", "data")]
    tech_spec = state.get("tech_spec", {})

    all_specs = _get_file_specs(state)

    if not all_specs:
        print("  ⚠️  No backend files in project_structure. Using minimal fallback.")
        all_specs = [
            {"path": "backend/main.py", "instruction": "FastAPI app basica con health endpoint", "depends_on": []},
            {"path": "backend/requirements.txt", "instruction": "Dependencias Python", "depends_on": []},
        ]

    # Fix mode: only regenerate flagged files
    if fix_instructions:
        fix_paths = {f["path"] for f in fix_instructions}
        specs_to_run = [s for s in all_specs if s["path"] in fix_paths]
        if not specs_to_run:
            specs_to_run = all_specs
        print(f"  🔧 Fix mode: regenerating {len(specs_to_run)} files...")
    else:
        specs_to_run = all_specs
        print(f"  ⚙️  Building backend: {len(specs_to_run)} files from architect's plan...")

    files = []
    errors = []

    for i, spec in enumerate(specs_to_run):
        file_path = spec.get("path", f"backend/unknown_{i}.py")
        print(f"  [{i+1}/{len(specs_to_run)}] Generating {file_path}...")

        extra_instruction = ""
        if fix_instructions:
            for fix in fix_instructions:
                if fix["path"] == file_path:
                    extra_instruction = f"\n\nCORRECCION REQUERIDA:\n{fix['instruction']}"
                    break

        user_prompt = _build_file_prompt(state, spec, extra_instruction)

        try:
            result = await call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=50_000,
            )

            if "error" in result:
                print(f"    ⚠️  Failed: {result.get('error', 'unknown')[:80]}")
                errors.append(f"{file_path}: {result.get('error', '')[:80]}")
                files.append(GeneratedFile(
                    path=file_path,
                    content=f"# Generation failed for {file_path}\n# Error: {result.get('error', 'unknown')[:200]}\n",
                    us_ids=[], created_by="Backend Builder (error)",
                ))
                continue

            content = result.get("content", "")
            if not content:
                content = result.get("code", str(result))

            relevant_us = [us["id"] for us in user_stories]

            files.append(GeneratedFile(
                path=file_path,
                content=content,
                us_ids=relevant_us,
                created_by="Backend Builder" + (" (fix)" if fix_instructions else ""),
            ))

            lines = content.count("\n") + 1
            print(f"    ✅ {lines} lines generated")

        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
            errors.append(f"{file_path}: {str(e)[:100]}")
            files.append(GeneratedFile(
                path=file_path,
                content=f"# Exception generating {file_path}\n# {str(e)[:200]}\n",
                us_ids=[], created_by="Backend Builder (exception)",
            ))

    mode = "fix" if fix_instructions else "full"
    print(f"\n  ✅ Backend {mode} complete: {len(files)} files, {len(errors)} errors")

    return {
        "files": files,
        "reasoning": f"Generated {len(files)} backend files ({mode} mode, {len(errors)} errors).",
    }


def _build_file_prompt(state: AgentState, spec: dict, extra_instruction: str = "") -> str:
    """Build targeted prompt for a single backend file."""
    tech_spec = state.get("tech_spec", {})
    backend_spec = state.get("backend_spec", {})
    instruction = spec.get("instruction", spec.get("description", "Generate this file"))
    depends_on = spec.get("depends_on", [])

    context_parts = []
    path = spec.get("path", "")

    # Add data context for model/schema/db files
    if any(k in path for k in ["model", "schema", "database", "db"]):
        context_parts.append(f"DB Schema:\n{tech_spec.get('db_schema', 'N/A')}")
        context_parts.append(f"Data Models:\n{json.dumps(tech_spec.get('data_models', []), indent=2, ensure_ascii=False)}")

    # Add API context for router/endpoint files
    if any(k in path for k in ["router", "route", "endpoint", "main", "app"]):
        context_parts.append(f"API Endpoints:\n{json.dumps(tech_spec.get('api_endpoints', []), indent=2, ensure_ascii=False)}")

    # Add ML context
    if any(k in path for k in ["ml", "classif", "predict", "train"]):
        context_parts.append(f"ML Pipeline:\n{json.dumps(tech_spec.get('ml_pipeline', {}), indent=2, ensure_ascii=False)}")

    # Add GenAI context
    if any(k in path for k in ["genai", "llm", "ai_service", "plan"]):
        context_parts.append(f"GenAI Integration:\n{json.dumps(tech_spec.get('genai_integration', {}), indent=2, ensure_ascii=False)}")
        context_parts.append("IMPORTANTE: Si ANTHROPIC_API_KEY no esta configurada (vacia o None), el servicio debe devolver un texto placeholder/dummy en vez de crashear.")

    context = "\n\n".join(context_parts) if context_parts else ""

    # All backend files for import reference
    all_files = tech_spec.get("project_structure", {}).get("files", [])
    backend_files = [f["path"] for f in all_files if f.get("domain") == "backend"] if isinstance(all_files, list) else []

    # Import rules from architect
    import_rules = backend_spec.get("import_rules", "") if isinstance(backend_spec, dict) else ""

    return f"""ARCHIVO A GENERAR: {spec['path']}

INSTRUCCION DEL ARQUITECTO:
{instruction}{extra_instruction}

DEPENDENCIAS (archivos que este importa):
{json.dumps(depends_on)}

{f"REGLAS DE IMPORTS:{chr(10)}{import_rules}" if import_rules else ""}

OTROS ARCHIVOS BACKEND (para imports correctos):
{json.dumps(backend_files)}

BRIEF DEL PROYECTO:
\"\"\"{state['brief'][:500]}\"\"\"

{f"CONTEXTO TECNICO:{chr(10)}{context}" if context else ""}

Stack: FastAPI + SQLAlchemy sync + SQLite + passlib + anthropic SDK + scikit-learn + joblib

Genera el codigo completo de {spec['path']} en JSON."""