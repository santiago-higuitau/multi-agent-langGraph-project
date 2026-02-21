"""
DevOps Agent

Reads devops file specs from Architect's devops_spec (or tech_spec fallback).
Generates each infrastructure file individually via LLM.
Compatible with Docker and Podman.
"""

import json
from ..graph.state import AgentState, GeneratedFile
from ..services import call_llm


SYSTEM_PROMPT = """Eres un DevOps/SRE senior experto en Docker, Podman y despliegue de aplicaciones web.

Genera UNICAMENTE el contenido del archivo de infraestructura que se te pide. Debe ser:
1. FUNCIONAL — debe funcionar con `docker-compose up --build` sin errores
2. COMPATIBLE con Docker y Podman
3. Sin HEALTHCHECK en Dockerfiles (Podman OCI no lo soporta bien)

STACK:
- Backend: Python 3.11 + FastAPI + uvicorn, puerto 8000, SQLite (archivo local)
- Frontend: React 18 + Vite (build) + nginx, puerto 80
- BD: SQLite (archivo local dentro del contenedor backend, NO necesita servicio postgres)
- Reverse proxy: nginx en el contenedor frontend

REGLAS CRITICAS:

DOCKERFILES:
- backend/Dockerfile: context = ./backend (dentro de docker-compose: build: ./backend)
  - FROM python:3.11-slim
  - WORKDIR /app
  - COPY requirements.txt .
  - RUN pip install --no-cache-dir -r requirements.txt
  - COPY . .
  - RUN mkdir -p ml/models && python ml/train.py  (ENTRENAR MODELO ML DURANTE BUILD)
  - CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
  - EXPOSE 8000
  - NO HEALTHCHECK (Podman OCI no lo soporta)
  - NO instalar paquetes pesados (torch, spacy, nltk, tensorflow)
  - NO instalar asyncpg, psycopg2, python-jose (no se usan)
  - SI incluir scikit-learn y joblib en requirements.txt

- frontend/Dockerfile: context = ./frontend (build: ./frontend)
  - Stage 1: FROM node:18-alpine AS build
    - WORKDIR /app
    - COPY package.json .
    - RUN npm install (OBLIGATORIO: usar "npm install", NUNCA "npm ci" porque no hay package-lock.json)
    - COPY . .
    - RUN npm run build
  - Stage 2: FROM nginx:alpine
    - COPY --from=build /app/dist /usr/share/nginx/html
    - COPY nginx-site.conf /etc/nginx/conf.d/default.conf
    - EXPOSE 80
  - NO HEALTHCHECK

DOCKER-COMPOSE:
- version: '3.8'
- Servicios: backend, frontend (SOLO 2 servicios, SIN postgres)
- backend: build: ./backend, ports 8001:8000, environment ANTHROPIC_API_KEY
- frontend: build: ./frontend, ports 3000:80, depends_on backend
- NO usar dockerfile: con paths relativos (../). Solo build: ./carpeta
- NO incluir servicio postgres (usamos SQLite)
- NO HEALTHCHECK en ningun servicio

NGINX (frontend/nginx-site.conf):
- server listen 80
- location / { root /usr/share/nginx/html; try_files $uri /index.html; }
- location /api/ { proxy_pass http://backend:8000/api/; proxy_set_header Host $host; }

.ENV.EXAMPLE:
- ANTHROPIC_API_KEY=sk-ant-xxx
- (Solo eso. SQLite no necesita configuracion. Auth es dummy.)

README.MD:
- Titulo del proyecto
- Prerequisitos: Docker/Podman instalado y corriendo
- Como levantar: cp .env.example .env, editar ANTHROPIC_API_KEY, docker-compose up --build (o podman-compose up --build)
- URLs: frontend http://localhost:3000, backend http://localhost:8001, API docs http://localhost:8001/docs
- Credenciales de prueba (si hay seed data)
- Estructura del proyecto

RESPONDE UNICAMENTE con JSON valido (sin markdown):
{
  "content": "contenido completo del archivo",
  "description": "que hace este archivo en una linea"
}"""


def _get_file_specs(state: AgentState) -> list:
    """Extract devops file specs from architect's devops_spec or project_structure."""
    devops_spec = state.get("devops_spec")
    if devops_spec and isinstance(devops_spec, dict):
        files = devops_spec.get("files", [])
        if files:
            return files

    tech_spec = state.get("tech_spec", {})
    project_structure = tech_spec.get("project_structure", {})

    files = project_structure.get("files", [])
    if isinstance(files, list) and len(files) > 0:
        devops_files = [f for f in files if f.get("domain") == "devops"]
        if devops_files:
            return devops_files

    # Fallback: minimum devops files
    return [
        {"path": "backend/Dockerfile", "instruction": "Dockerfile para FastAPI. python:3.11-slim, pip install requirements.txt, COPY . ., CMD uvicorn main:app. EXPOSE 8000. SIN HEALTHCHECK.", "domain": "devops", "depends_on": []},
        {"path": "frontend/Dockerfile", "instruction": "Dockerfile multi-stage. node:18-alpine build (npm install, NO npm ci) + nginx:alpine. SIN HEALTHCHECK.", "domain": "devops", "depends_on": []},
        {"path": "frontend/nginx-site.conf", "instruction": "nginx config: serve SPA con try_files, proxy /api/ a backend:8000.", "domain": "devops", "depends_on": []},
        {"path": "docker-compose.yml", "instruction": "docker-compose: backend (8001:8000) + frontend (3000:80). SIN postgres. SIN HEALTHCHECK. environment ANTHROPIC_API_KEY.", "domain": "devops", "depends_on": []},
        {"path": ".env.example", "instruction": "Solo ANTHROPIC_API_KEY=sk-ant-xxx. Nada mas.", "domain": "devops", "depends_on": []},
        {"path": "README.md", "instruction": "README: prerequisitos (Docker/Podman), como levantar (cp .env.example .env, editar key, docker-compose up --build o podman-compose up --build), URLs, credenciales test.", "domain": "devops", "depends_on": []},
    ]


async def run_devops_agent(state: AgentState) -> dict:
    """Generate DevOps files one by one."""
    all_specs = _get_file_specs(state)

    print(f"  🚀 Generating {len(all_specs)} infrastructure files...")

    files = []
    errors = []

    for i, spec in enumerate(all_specs):
        file_path = spec.get("path", f"unknown_{i}")
        print(f"  [{i+1}/{len(all_specs)}] Generating {file_path}...")

        user_prompt = _build_file_prompt(state, spec)

        try:
            result = await call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=50_000,
            )

            if "error" in result:
                print(f"    ⚠️  Failed: {result.get('error', 'unknown')[:80]}")
                errors.append(f"{file_path}: {result.get('error', '')[:80]}")
                continue

            content = result.get("content", "")
            if not content:
                content = result.get("code", str(result))

            files.append(GeneratedFile(
                path=file_path,
                content=content,
                us_ids=[],
                created_by="DevOps Agent",
            ))

            lines = content.count("\n") + 1
            print(f"    ✅ {lines} lines generated")

        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
            errors.append(f"{file_path}: {str(e)[:100]}")

    print(f"\n  ✅ DevOps complete: {len(files)} files, {len(errors)} errors")

    if not files:
        return _fallback(state)

    return {
        "files": files,
        "reasoning": f"Generated {len(files)} infrastructure files.",
    }


def _build_file_prompt(state: AgentState, spec: dict) -> str:
    """Build prompt for a single DevOps file."""
    tech_spec = state.get("tech_spec", {})
    generated_files = state.get("generated_files", [])
    instruction = spec.get("instruction", spec.get("description", "Generate this file"))

    file_list = [f["path"] for f in generated_files]

    # Find dependency files
    deps = {}
    for f in generated_files:
        if "requirements.txt" in f["path"]:
            deps["backend_requirements"] = f["content"]
        if "package.json" in f["path"]:
            deps["frontend_package_json"] = f["content"]

    context_parts = [
        f"Stack: {json.dumps(tech_spec.get('stack', {}), ensure_ascii=False)}",
    ]

    path = spec.get("path", "")

    if "init_db" in path or "sql" in path:
        context_parts.append(f"DB Schema:\n{tech_spec.get('db_schema', 'N/A')}")

    if "docker-compose" in path or "Dockerfile" in path or "README" in path:
        context_parts.append(f"Archivos del proyecto:\n{json.dumps(file_list, indent=2)}")
        if deps:
            context_parts.append(f"Dependencias:\n{json.dumps(deps, indent=2, ensure_ascii=False)}")

    if "README" in path:
        context_parts.append(f"API Endpoints:\n{json.dumps(tech_spec.get('api_endpoints', []), indent=2, ensure_ascii=False)}")

    context = "\n\n".join(context_parts)

    return f"""ARCHIVO A GENERAR: {spec['path']}

INSTRUCCION DEL ARQUITECTO:
{instruction}

BRIEF DEL PROYECTO:
\"\"\"{state['brief'][:300]}\"\"\"

CONTEXTO:
{context}

Genera el contenido completo de {spec['path']} en JSON."""


def _fallback(state):
    return {
        "files": [
            GeneratedFile(
                path="docker-compose.yml",
                content="version: '3.8'\nservices:\n  backend:\n    build: ./backend\n    ports:\n      - '8001:8000'\n",
                us_ids=[], created_by="DevOps Agent (fallback)",
            ),
            GeneratedFile(
                path="README.md",
                content="# Project\n\nDevOps generation failed. Run manually:\n```\ncd backend && uvicorn main:app --reload\n```\n",
                us_ids=[], created_by="DevOps Agent (fallback)",
            ),
        ],
        "reasoning": "Fallback: LLM calls failed.",
    }