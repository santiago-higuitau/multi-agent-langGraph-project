"""
Frontend Builder Agent

Reads file specs from Architect's frontend_spec (or tech_spec fallback).
Generates each frontend file individually via LLM.
Designed for parallel execution with backend_builder.
"""

import json
from ..graph.state import AgentState, GeneratedFile
from ..services import call_llm


SYSTEM_PROMPT = """Eres un desarrollador frontend senior experto en React 18, Vite y TailwindCSS.

Genera UNICAMENTE el codigo del archivo que se te pide. El codigo debe ser:
1. COMPLETO y funcional (no placeholders, no TODOs)
2. React 18 con hooks (useState, useEffect, useCallback, useMemo)
3. TailwindCSS para TODOS los estilos (no CSS custom, no style={{}})
4. Responsive y profesional
5. Manejo de estados: loading, error, empty state
6. Los endpoints API deben coincidir EXACTAMENTE con los de la tech spec

STACK:
- React 18 + Vite 5 + TailwindCSS 3
- React Router v6 (BrowserRouter, Routes, Route, useNavigate, useParams, Link)
- Axios para HTTP (instancia centralizada en services/api.js)
- Recharts para graficos (BarChart, PieChart, LineChart, ResponsiveContainer)
- Auth: Token simple en localStorage, header Authorization: Bearer {token}. Login envia email+password, recibe token. SIN JWT decode en frontend.

REGLAS DE IMPORTS:
- import api from '../services/api' (o '../../services/api' segun profundidad)
- import { useNavigate } from 'react-router-dom'
- import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
- Componentes: export default function ComponentName() { ... }

REGLAS DE CODIGO:
- package.json: usar "type": "module", scripts: {"dev": "vite", "build": "vite build", "preview": "vite preview"}
- vite.config.js: proxy /api a http://backend:8000 (para Docker) o http://localhost:8000 (dev)
- api.js: baseURL = '/api', interceptor que agrega Authorization header, interceptor 401 que redirige a /login
- Paginas: usar useEffect para fetch inicial, useState para data/loading/error
- Formularios: useState por campo, onSubmit async con try/catch
- Tablas: mapear arrays con .map(), key={item.id}
- Graficos: Recharts con ResponsiveContainer width="100%" height={300}

RESPONDE UNICAMENTE con JSON valido (sin markdown):
{
    "content": "codigo completo del archivo",
    "description": "que hace este archivo en una linea"
}"""


def _get_file_specs(state: AgentState) -> list:
    """Extract frontend file specs from architect's frontend_spec or project_structure."""
    frontend_spec = state.get("frontend_spec")
    if frontend_spec and isinstance(frontend_spec, dict):
        files = frontend_spec.get("files", [])
        if files:
            return files

    tech_spec = state.get("tech_spec", {})
    project_structure = tech_spec.get("project_structure", {})

    files = project_structure.get("files", [])
    if isinstance(files, list) and len(files) > 0:
        return [f for f in files if f.get("domain") == "frontend"]

    # Legacy format
    specs = []
    frontend_structure = project_structure.get("frontend/", project_structure.get("frontend", {}))
    if isinstance(frontend_structure, dict):
        for filename, description in frontend_structure.items():
            if isinstance(description, str):
                specs.append({"path": f"frontend/{filename}", "description": description, "instruction": description, "depends_on": []})
            elif isinstance(description, dict):
                for sub_file, sub_desc in description.items():
                    path_prefix = filename if filename.endswith("/") else f"{filename}/"
                    specs.append({"path": f"frontend/{path_prefix}{sub_file}", "description": str(sub_desc), "instruction": str(sub_desc), "depends_on": []})

    return specs


async def run_frontend_builder(state: AgentState, fix_instructions: list = None) -> dict:
    """Generate frontend files one by one from tech spec."""
    user_stories = [us for us in state["user_stories"] if us.get("domain") == "frontend"]
    all_stories = state["user_stories"]
    tech_spec = state.get("tech_spec", {})

    all_specs = _get_file_specs(state)

    if not all_specs:
        print("  ⚠️  No frontend files in project_structure. Using minimal fallback.")
        all_specs = [
            {"path": "frontend/package.json", "instruction": "package.json con React 18, Vite, TailwindCSS, axios, recharts, react-router-dom v6", "depends_on": []},
            {"path": "frontend/index.html", "instruction": "HTML base con div#root y script module a /src/main.jsx", "depends_on": []},
            {"path": "frontend/src/main.jsx", "instruction": "Entry point: ReactDOM.createRoot, BrowserRouter, App", "depends_on": []},
            {"path": "frontend/src/App.jsx", "instruction": "Componente principal con React Router y layout basico", "depends_on": []},
        ]

    # Fix mode
    if fix_instructions:
        fix_paths = {f["path"] for f in fix_instructions}
        specs_to_run = [s for s in all_specs if s["path"] in fix_paths]
        if not specs_to_run:
            specs_to_run = all_specs
        print(f"  🔧 Fix mode: regenerating {len(specs_to_run)} files...")
    else:
        specs_to_run = all_specs
        print(f"  🎨 Building frontend: {len(specs_to_run)} files from architect's plan...")

    files = []
    errors = []

    for i, spec in enumerate(specs_to_run):
        file_path = spec.get("path", f"frontend/src/unknown_{i}.jsx")
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
                agent="frontend_builder",
            )

            if "error" in result:
                print(f"    ⚠️  Failed: {result.get('error', 'unknown')[:80]}")
                errors.append(f"{file_path}: {result.get('error', '')[:80]}")
                files.append(GeneratedFile(
                    path=file_path,
                    content=f"// Generation failed for {file_path}\n",
                    us_ids=[], created_by="Frontend Builder (error)",
                ))
                continue

            content = result.get("content", "")
            if not content:
                content = result.get("code", str(result))

            us_ids = [us["id"] for us in user_stories]

            files.append(GeneratedFile(
                path=file_path,
                content=content,
                us_ids=us_ids,
                created_by="Frontend Builder" + (" (fix)" if fix_instructions else ""),
            ))

            lines = content.count("\n") + 1
            print(f"    ✅ {lines} lines generated")

        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
            errors.append(f"{file_path}: {str(e)[:100]}")
            files.append(GeneratedFile(
                path=file_path,
                content=f"// Exception generating {file_path}\n// {str(e)[:200]}\n",
                us_ids=[], created_by="Frontend Builder (exception)",
            ))

    mode = "fix" if fix_instructions else "full"
    print(f"\n  ✅ Frontend {mode} complete: {len(files)} files, {len(errors)} errors")

    return {
        "files": files,
        "reasoning": f"Generated {len(files)} frontend files ({mode} mode, {len(errors)} errors).",
    }


def _build_file_prompt(state: AgentState, spec: dict, extra_instruction: str = "") -> str:
    """Build targeted prompt for a single frontend file."""
    tech_spec = state.get("tech_spec", {})
    instruction = spec.get("instruction", spec.get("description", "Generate this file"))
    depends_on = spec.get("depends_on", [])
    all_stories = state["user_stories"]

    context_parts = []
    path = spec.get("path", "")

    # API service files need endpoint list
    if any(k in path for k in ["api", "service", "http", "client"]):
        context_parts.append(f"API Endpoints (para construir las llamadas):\n{json.dumps(tech_spec.get('api_endpoints', []), indent=2, ensure_ascii=False)}")

    # Component/page files need data models + endpoints
    if any(k in path.lower() for k in ["component", "page", "dashboard", "list", "form", "detail", "login"]):
        context_parts.append(f"API Endpoints:\n{json.dumps(tech_spec.get('api_endpoints', []), indent=2, ensure_ascii=False)}")
        context_parts.append(f"Data Models:\n{json.dumps(tech_spec.get('data_models', []), indent=2, ensure_ascii=False)}")

    # App.jsx needs list of all components/pages
    if "App" in path:
        all_files = tech_spec.get("project_structure", {}).get("files", [])
        frontend_files = [f["path"] for f in all_files if f.get("domain") == "frontend"] if isinstance(all_files, list) else []
        context_parts.append(f"Todos los archivos frontend (para imports y rutas):\n{json.dumps(frontend_files)}")

    context = "\n\n".join(context_parts) if context_parts else ""

    # All frontend files for reference
    all_files = tech_spec.get("project_structure", {}).get("files", [])
    frontend_files = [f["path"] for f in all_files if f.get("domain") == "frontend"] if isinstance(all_files, list) else []

    # Auth flow from frontend_spec
    frontend_spec = state.get("frontend_spec", {})
    auth_flow = frontend_spec.get("auth_flow", "") if isinstance(frontend_spec, dict) else ""

    return f"""ARCHIVO A GENERAR: {spec['path']}

INSTRUCCION DEL ARQUITECTO:
{instruction}{extra_instruction}

DEPENDENCIAS:
{json.dumps(depends_on)}

OTROS ARCHIVOS FRONTEND (para imports):
{json.dumps(frontend_files)}

{f"AUTH FLOW:{chr(10)}{auth_flow}" if auth_flow else ""}

BRIEF DEL PROYECTO:
\"\"\"{state['brief'][:500]}\"\"\"

USER STORIES (contexto):
{json.dumps(all_stories[:5], indent=2, ensure_ascii=False)}

{f"CONTEXTO TECNICO:{chr(10)}{context}" if context else ""}

Stack: React 18 + Vite 5 + TailwindCSS 3 + Axios + Recharts + React Router v6

Genera el codigo completo de {spec['path']} en JSON."""