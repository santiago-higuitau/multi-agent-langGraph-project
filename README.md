# 🤖 AI Dev Team

Sistema multi-agente que transforma un brief en una aplicación funcional completa.

Recibe una descripción de lo que quieres construir, y un pipeline de 9 agentes de IA
(BA, PO, Arquitecto, Evaluador, Backend Builder, Frontend Builder, QA, Integración, DevOps)
genera requerimientos, historias de usuario, arquitectura, código, tests y configuración
de despliegue — todo automatizado con revisión humana en dos puntos clave.

## Stack

- **Backend (orquestador):** Python 3.11+ · FastAPI · LangGraph · Anthropic SDK
- **Frontend (panel de control):** React 18 · Vite · TailwindCSS
- **LLM:** Multi-proveedor — Anthropic, OpenAI, Groq, Gemini, Kimi, Mistral

## Requisitos previos

- Python 3.11+
- Node.js 18+
- Una API key de Anthropic (o del provider que elijas)

## Setup rápido

### 1. Clonar y configurar variables de entorno

```bash
git clone <repo-url>
cd ai-dev-team
cp .env.example .env
# Edita .env y agrega tu ANTHROPIC_API_KEY
```

### 2. Backend

```bash
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Ejecutar

Necesitas dos terminales:

**Terminal 1 — Backend (puerto 8000):**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend (puerto 5173):**
```bash
cd frontend
npm run dev
```

Abre http://localhost:5173 en tu navegador.

## Cómo funciona

1. **Nuevo Run** — Escribe un brief describiendo la aplicación que quieres
2. **Pipeline automático** — Los agentes trabajan en secuencia:
   - BA analiza requerimientos → PO prioriza y define MVP → Arquitecto diseña → Evaluador valida
3. **Gate 1** — Revisas la planificación y apruebas (o pides cambios)
4. **Construcción** — Backend y Frontend builders generan código en paralelo → QA genera tests
5. **Integración** — Validación cruzada del código generado
6. **Gate 2** — Revisas el código y apruebas
7. **DevOps** — Genera Dockerfile, docker-compose, nginx, README
8. **Exportar** — Descarga un ZIP con el proyecto completo listo para `docker-compose up`

## Estructura del proyecto

```
├── backend/              # Orquestador multi-agente (FastAPI + LangGraph)
│   ├── agents/           # 9 agentes especializados
│   ├── api/              # Endpoints REST
│   ├── graph/            # Workflow LangGraph (state, nodes, edges)
│   └── services/         # Servicio LLM (Anthropic/OpenAI/Groq/Kimi)
├── frontend/             # Panel de control (React + Vite + Tailwind)
│   └── src/
│       ├── components/   # PipelineTracker, ArtifactsPanel, FilesPanel, etc.
│       ├── pages/        # HomePage, RunPage, RunsListPage
│       └── services/     # Cliente API (axios)
├── app/                  # Output: aquí se exportan las apps generadas
├── exports/              # ZIPs descargables
├── .env.example          # Template de configuración
└── requirements.txt      # Dependencias Python
```

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/runs` | Iniciar un nuevo run con un brief |
| GET | `/api/runs` | Listar todos los runs |
| GET | `/api/runs/{id}` | Estado actual de un run |
| GET | `/api/runs/{id}/artifacts` | Artefactos generados |
| GET | `/api/runs/{id}/files` | Archivos generados con contenido |
| GET | `/api/runs/{id}/decisions` | Log de decisiones de agentes |
| POST | `/api/runs/{id}/hitl` | Enviar decisión HITL (aprobar/rechazar) |
| POST | `/api/runs/{id}/export` | Exportar proyecto a app/ + ZIP |
| GET | `/api/runs/{id}/download` | Descargar ZIP |
| POST | `/api/deploy` | Desplegar con docker-compose |
| POST | `/api/teardown` | Detener contenedores |

## Configuración LLM

Cada agente usa su propio modelo, configurable por variable de entorno. El formato es `provider/model-id`.

### Variables de entorno

```bash
# Fallback para agentes sin override explícito
DEFAULT_MODEL=anthropic/claude-sonnet-4-6

# API keys — solo las del provider que uses
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...

# Modelo por agente (opcional — si no se define, usa DEFAULT_MODEL)
MODEL_BA=anthropic/claude-sonnet-4-6
MODEL_PO=anthropic/claude-sonnet-4-6
MODEL_ARCHITECT=anthropic/claude-opus-4-6
MODEL_BACKEND=anthropic/claude-sonnet-4-6
MODEL_FRONTEND=anthropic/claude-sonnet-4-6
MODEL_QA=anthropic/claude-haiku-4-5-20251001
MODEL_VALIDATOR=anthropic/claude-opus-4-6
MODEL_DEVOPS=anthropic/claude-haiku-4-5-20251001
MODEL_EVALUATOR=anthropic/claude-sonnet-4-6
```

### Providers soportados

| Provider | Formato | API Key |
|----------|---------|---------|
| Anthropic | `anthropic/claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Gemini | `gemini/gemini-1.5-pro` | `GEMINI_API_KEY` |
| Kimi | `kimi/moonshot-v1-8k` | `KIMI_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |

Puedes mezclar proveedores libremente — por ejemplo, Anthropic Opus para el Arquitecto y Groq para los builders.
