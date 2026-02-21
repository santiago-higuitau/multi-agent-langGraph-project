"""
QA Agent

Generates test files dynamically from architect's qa_spec.
Each test file is generated in a separate LLM call.
Falls back to generating tests based on generated backend files if no qa_spec.
"""

import json
from ..graph.state import AgentState, TestCase, GeneratedFile
from ..services import call_llm


SYSTEM_PROMPT = """Eres un QA Engineer senior experto en pytest y testing de APIs FastAPI.

Genera UNICAMENTE el codigo del archivo de test que se te pide. El codigo debe ser:
1. EJECUTABLE con pytest (sin errores de sintaxis ni imports faltantes)
2. Usar pytest con fixtures, parametrize donde aplique
3. Usar httpx.AsyncClient para tests de endpoints FastAPI (async)
4. Usar unittest.mock.patch / AsyncMock para mockear servicios externos (GenAI, etc.)
5. Nombres descriptivos: test_should_xxx_when_yyy
6. Asserts especificos: status code, campos en response, tipos de datos
7. Tests independientes entre si (no dependen de orden de ejecucion)

STACK DE TESTING:
- pytest + pytest-asyncio
- httpx (TestClient sync para FastAPI)
- unittest.mock (patch, MagicMock, AsyncMock)
- SQLite en memoria para tests de BD

REGLAS DE IMPORTS EN TESTS:
- from main import app (la FastAPI app)
- from models import Base, User, {Modelo}
- from auth import create_session_token
- from database import get_db
- NUNCA: from backend.xxx, from app.xxx

PATRON DE CONFTEST:
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from models import Base
from database import get_db

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

RESPONDE UNICAMENTE con JSON valido (sin markdown):
{
  "content": "codigo pytest completo del archivo",
  "test_cases": [
    {"id": "TC-001", "title": "Titulo del caso de prueba", "us_id": "US-001", "type": "integration|unit"}
  ]
}"""


def _get_test_specs(state: AgentState) -> list:
    """Get test file specs from architect's qa_spec or generate from backend files."""
    qa_spec = state.get("qa_spec")
    if qa_spec and isinstance(qa_spec, dict):
        test_files = qa_spec.get("test_files", [])
        if test_files:
            return test_files

    # Fallback: generate test specs from generated backend files
    generated_files = state.get("generated_files", [])
    backend_files = [f for f in generated_files if f["path"].startswith("backend/") and not f["path"].startswith("backend/tests/")]

    specs = [
        {"path": "backend/tests/conftest.py", "instruction": "Genera conftest.py con fixtures: async_session (SQLite en memoria), client (httpx.AsyncClient con override de get_db), auth_token (JWT valido para tests). Usa pytest-asyncio.", "focus_us": []},
    ]

    # Generate a test file for each router
    for f in backend_files:
        if "router" in f["path"]:
            name = f["path"].split("/")[-1].replace("_router.py", "").replace(".py", "")
            specs.append({
                "path": f"backend/tests/test_{name}.py",
                "instruction": f"Genera tests para los endpoints del router {f['path']}. Incluye: crear recurso (201), listar (200), obtener por ID (200), ID inexistente (404), campos invalidos (422). Minimo 5 tests.",
                "focus_us": [],
            })

    # Test for ML service
    ml_files = [f for f in backend_files if "ml" in f["path"]]
    if ml_files:
        specs.append({
            "path": "backend/tests/test_ml_service.py",
            "instruction": "Genera tests para el servicio ML: clasificacion correcta por keywords, texto ambiguo con baja confianza, texto vacio. Minimo 4 tests.",
            "focus_us": [],
        })

    # Test for GenAI service
    genai_files = [f for f in backend_files if "genai" in f["path"]]
    if genai_files:
        specs.append({
            "path": "backend/tests/test_genai_service.py",
            "instruction": "Genera tests para el servicio GenAI: mockear Anthropic API, verificar estructura de respuesta, manejar error de API, timeout. Usa unittest.mock.patch. Minimo 4 tests.",
            "focus_us": [],
        })

    # Test for auth
    auth_files = [f for f in backend_files if "auth" in f["path"]]
    if auth_files:
        specs.append({
            "path": "backend/tests/test_auth.py",
            "instruction": "Genera tests para autenticacion: login exitoso, credenciales invalidas (401), acceso sin token (401), token expirado (401). Minimo 4 tests.",
            "focus_us": [],
        })

    return specs


async def run_qa_agent(state: AgentState) -> dict:
    """Generate test cases and test files dynamically."""
    user_stories = state["user_stories"]
    test_specs = _get_test_specs(state)

    print(f"  🧪 Generating {len(test_specs)} test files...")

    all_test_cases = []
    all_test_files = []
    errors = []
    tc_counter = 1

    for i, spec in enumerate(test_specs):
        file_path = spec["path"]
        print(f"  [{i+1}/{len(test_specs)}] Generating {file_path}...")

        user_prompt = _build_test_prompt(state, spec)

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
                continue

            content = result.get("content", "")
            if not content:
                content = str(result)

            raw_tcs = result.get("test_cases", [])
            for tc in raw_tcs:
                tc_id = f"TC-{str(tc_counter).zfill(3)}"
                all_test_cases.append(TestCase(
                    id=tc_id,
                    title=tc.get("title", f"Test {tc_counter}"),
                    description=tc.get("title", ""),
                    preconditions=["System running", "Test DB initialized"],
                    steps=["Execute pytest"],
                    expected_result="Pass",
                    us_id=tc.get("us_id", ""),
                    type=tc.get("type", "integration"),
                    created_by="QA Agent",
                ))
                tc_counter += 1

            all_test_files.append(GeneratedFile(
                path=file_path,
                content=content,
                us_ids=spec.get("focus_us", []),
                created_by="QA Agent",
            ))

            lines = content.count("\n") + 1
            print(f"    ✅ {lines} lines, {len(raw_tcs)} test cases")

        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
            errors.append(f"{file_path}: {str(e)[:100]}")

    if not all_test_cases:
        for j, us in enumerate(user_stories):
            all_test_cases.append(TestCase(
                id=f"TC-{str(j+1).zfill(3)}",
                title=f"Test for {us['title']}",
                description=f"Verify: {us['title']}",
                preconditions=["System running"],
                steps=us.get("acceptance_criteria", ["Execute test"]),
                expected_result="All acceptance criteria pass",
                us_id=us["id"],
                type="acceptance",
                created_by="QA Agent",
            ))

    print(f"\n  ✅ QA complete: {len(all_test_cases)} TCs, {len(all_test_files)} files, {len(errors)} errors")

    return {
        "test_cases": all_test_cases,
        "test_files": all_test_files,
        "test_results": {
            "total": len(all_test_cases),
            "documented": len(all_test_cases),
            "automated": len(all_test_files),
        },
        "reasoning": f"Generated {len(all_test_cases)} test cases and {len(all_test_files)} test files.",
    }


def _build_test_prompt(state: AgentState, spec: dict) -> str:
    tech_spec = state.get("tech_spec", {})

    relevant_stories = []
    if spec.get("focus_us"):
        relevant_stories = [us for us in state["user_stories"] if us["id"] in spec["focus_us"]]
    else:
        relevant_stories = state["user_stories"][:3]

    # Get generated backend file contents for context
    generated_files = state.get("generated_files", [])
    backend_files = [f["path"] for f in generated_files if f["path"].startswith("backend/")]

    # Find the source file this test is testing
    test_name = spec["path"].split("/")[-1].replace("test_", "").replace(".py", "")
    source_content = ""
    for f in generated_files:
        if test_name in f["path"] and not f["path"].startswith("backend/tests/"):
            source_content = f["content"][:3000]
            break

    return f"""ARCHIVO DE TEST: {spec['path']}

INSTRUCCION:
{spec['instruction']}

{f"CODIGO FUENTE A TESTEAR:{chr(10)}{source_content}" if source_content else ""}

USER STORIES:
{json.dumps(relevant_stories, indent=2, ensure_ascii=False)}

API ENDPOINTS:
{json.dumps(tech_spec.get('api_endpoints', []), indent=2, ensure_ascii=False)}

ARCHIVOS BACKEND (para imports):
{json.dumps(backend_files, indent=2)}

Stack: FastAPI + SQLAlchemy sync + pytest + httpx + SQLite

Genera el codigo completo en JSON."""