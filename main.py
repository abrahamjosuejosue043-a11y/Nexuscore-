"""
NEXUSCORE AI — API CENTRAL
Arquivo: main.py (raiz do repositório)

Esta versão mantém as rotas principais do projeto e organiza:
- Inicialização do FastAPI
- Comunicação assíncrona com Gemini e Groq
- Orquestração com fallback transparente
- Diagnóstico administrativo protegido
- Entrega do frontend/frontend index.html

IMPORTANTE:
- Groq é o provedor da API usada pelo módulo Llama; não é a API da Meta.
- Esta versão ainda NÃO implementa colaboração real entre três agentes.
- Os endpoints de e-mail respondem como não implementados até existir
  integração real com backend/email_services.py.
"""

import os
import re
import time
import hmac
import logging
from pathlib import Path
from collections import OrderedDict
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.cerebro1_gemini import (
    chamar_gemini as chamar_gemini_modulo,
    GeminiError,
)


# ---------------------------------------------------------------------------
# Configuração geral
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = BASE_DIR / "frontend" / "index.html"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("nexuscore")

APP_NAME = "Nexuscore AI"
APP_VERSION = "1.0.0"

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

REQUEST_TIMEOUT = float(os.getenv("AI_REQUEST_TIMEOUT", "45"))
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "8000"))
CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "100"))

# Cache temporário limitado. Não substitui o futuro banco de dados.
_RESPONSE_CACHE: OrderedDict[str, dict] = OrderedDict()


def get_secret(name: str) -> Optional[str]:
    """Lê uma variável de ambiente sem expor seu valor nos logs ou respostas."""
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return value.strip('"').strip("'")


def get_cors_origins() -> list[str]:
    """
    CORS configurável.
    Em produção, informe CORS_ORIGINS com as origens permitidas separadas por vírgula.
    Exemplo: https://seu-dominio.onrender.com
    """
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API central do Nexuscore AI.",
)

allowed_origins = get_cors_origins()
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )


# ---------------------------------------------------------------------------
# Modelos de entrada
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARS)
    tipo: str = Field(default="geral", max_length=40)


class EmailRequest(BaseModel):
    texto: str = Field(default="", max_length=MAX_INPUT_CHARS)
    assunto: str = Field(default="", max_length=300)
    destinatario: str = Field(default="", max_length=320)


# ---------------------------------------------------------------------------
# Erros controlados dos provedores
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int = 502):
        self.provider = provider
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def extract_provider_error(response: httpx.Response) -> str:
    """Extrai uma mensagem curta de erro sem incluir cabeçalhos ou chaves."""
    try:
        data = response.json()
        error = data.get("error", {})
        if isinstance(error, dict):
            message = error.get("message") or error.get("status")
            if message:
                return str(message)[:500]
        if isinstance(error, str):
            return error[:500]
    except Exception:
        pass
    return response.text[:300] or f"HTTP {response.status_code}"


# ---------------------------------------------------------------------------
# Integração Gemini — delegada ao módulo backend/cerebro1_gemini.py
# ---------------------------------------------------------------------------

async def chamar_gemini(prompt: str) -> str:
    try:
        return await chamar_gemini_modulo(prompt)
    except GeminiError as erro:
        raise ProviderError("Gemini", str(erro), 502) from erro


# ---------------------------------------------------------------------------
# Integração Groq (modelos Llama)
# ---------------------------------------------------------------------------

async def chamar_groq(prompt: str) -> str:
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        raise ProviderError(
            "Groq",
            "A variável GROQ_API_KEY não está configurada no ambiente do serviço.",
            503,
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
    except httpx.TimeoutException:
        raise ProviderError("Groq", "Tempo limite excedido ao consultar a Groq.", 504)
    except httpx.HTTPError as exc:
        logger.warning("Falha de conexão com Groq: %s", type(exc).__name__)
        raise ProviderError("Groq", "Não foi possível conectar à Groq.", 502)

    if response.status_code != 200:
        detail = extract_provider_error(response)
        if response.status_code in (400, 401, 403):
            message = f"Groq recusou a solicitação (HTTP {response.status_code}). Verifique a chave, o modelo e as permissões."
        elif response.status_code == 404:
            message = f"Modelo Groq '{GROQ_MODEL}' não encontrado ou indisponível."
        elif response.status_code == 429:
            message = "Limite de solicitações da Groq atingido. Tente novamente mais tarde."
        else:
            message = f"Groq retornou HTTP {response.status_code}."
        logger.warning("Groq HTTP %s: %s", response.status_code, detail)
        raise ProviderError("Groq", message, 502)

    try:
        data = response.json()
        choices = data.get("choices") or []
        answer = choices[0].get("message", {}).get("content", "") if choices else ""
        if isinstance(answer, list):
            answer = "\n".join(
                item.get("text", "") for item in answer if isinstance(item, dict)
            )
        answer = str(answer).strip()
    except (ValueError, IndexError, AttributeError, TypeError):
        answer = ""

    if not answer:
        raise ProviderError("Groq", "A Groq respondeu sem conteúdo de texto.", 502)
    return answer


# ---------------------------------------------------------------------------
# Orquestração básica — fallback, ainda sem agentes colaborativos
# ---------------------------------------------------------------------------

def normalize_type(value: str) -> str:
    value = (value or "geral").strip().lower()
    aliases = {
        "codigo": "programacao",
        "código": "programacao",
        "engenharia": "programacao",
        "marketing": "publicidade",
        "direcao": "diretoria",
        "direção": "diretoria",
    }
    value = aliases.get(value, value)
    if value not in {"geral", "diretoria", "programacao", "publicidade"}:
        return "geral"
    return value


def build_prompt(text: str, agent_type: str) -> str:
    instructions = {
        "diretoria": (
            "Você é o agente de Diretoria do Nexuscore AI. "
            "Analise objetivos, riscos, prioridades e próximos passos. "
            "Não afirme que executou tarefas que não realizou."
        ),
        "programacao": (
            "Você é o agente de Engenharia de Software do Nexuscore AI. "
            "Entregue soluções técnicas claras, seguras e testáveis. "
            "Ao propor alterações, indique arquivos e passos de validação. "
            "Não afirme que executou ou testou código sem realmente fazê-lo."
        ),
        "publicidade": (
            "Você é o agente de Marketing do Nexuscore AI. "
            "Analise público, proposta de valor, posicionamento e aquisição. "
            "Diferencie hipóteses de fatos comprovados."
        ),
        "geral": (
            "Você é o assistente central do Nexuscore AI. "
            "Responda com clareza, precisão e transparência."
        ),
    }
    return f"{instructions[agent_type]}\n\nSolicitação do usuário:\n{text}"


def cache_get(key: str) -> Optional[dict]:
    result = _RESPONSE_CACHE.get(key)
    if result is not None:
        _RESPONSE_CACHE.move_to_end(key)
        return dict(result)
    return None


def cache_set(key: str, value: dict) -> None:
    _RESPONSE_CACHE[key] = dict(value)
    _RESPONSE_CACHE.move_to_end(key)
    while len(_RESPONSE_CACHE) > max(1, CACHE_MAX_ITEMS):
        _RESPONSE_CACHE.popitem(last=False)


async def orquestrador(pedido: str, tipo: str = "geral") -> dict:
    started = time.perf_counter()
    text = (pedido or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="O texto da mensagem está vazio.")

    agent_type = normalize_type(tipo)
    cache_key = f"{agent_type}:{text.casefold()}"
    cached = cache_get(cache_key)
    if cached:
        cached["origem"] = "cache_temporario"
        cached["tempo_ms"] = int((time.perf_counter() - started) * 1000)
        return cached

    prompt = build_prompt(text, agent_type)

    # Engenharia prefere Groq; os demais tipos preferem Gemini.
    providers = (
        [("Groq", chamar_groq), ("Gemini", chamar_gemini)]
        if agent_type == "programacao"
        else [("Gemini", chamar_gemini), ("Groq", chamar_groq)]
    )

    errors = []
    for provider_name, provider_function in providers:
        try:
            answer = await provider_function(prompt)
            result = {
                "resposta": answer,
                "origem": provider_name.lower(),
                "cerebro": provider_name,
                "tempo_ms": int((time.perf_counter() - started) * 1000),
            }
            cache_set(cache_key, result)
            return result
        except ProviderError as exc:
            errors.append(f"{exc.provider}: {exc.message}")
            logger.info("%s indisponível: %s", exc.provider, exc.message)

    raise HTTPException(
        status_code=502,
        detail={
            "mensagem": "Nenhum provedor de IA conseguiu responder.",
            "motivos": errors,
            "orientacao": (
                "Confira GEMINI_API_KEY e GROQ_API_KEY no ambiente do serviço "
                "e confirme se os modelos configurados estão disponíveis."
            ),
        },
    )


# ---------------------------------------------------------------------------
# Segurança administrativa
# ---------------------------------------------------------------------------

def require_admin_token(token: Optional[str]) -> None:
    expected = get_secret("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Diagnóstico administrativo desativado: configure ADMIN_TOKEN no ambiente.",
        )
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Acesso administrativo não autorizado.")


# ---------------------------------------------------------------------------
# Rotas de API
# ---------------------------------------------------------------------------

@app.get("/api/saude")
async def saude():
    """Verificação básica, sem revelar valores ou nomes de segredos."""
    return {
        "status": "ok",
        "sistema": APP_NAME,
        "versao": APP_VERSION,
        "provedores_configurados": {
            "gemini": bool(get_secret("GEMINI_API_KEY")),
            "groq": bool(get_secret("GROQ_API_KEY")),
        },
    }


@app.get("/api/diagnostico")
async def diagnostico(x_admin_token: Optional[str] = Header(default=None)):
    """Diagnóstico protegido pelo segredo ADMIN_TOKEN."""
    require_admin_token(x_admin_token)

    return {
        "sistema": APP_NAME,
        "variaveis": {
            "GEMINI_API_KEY": "configurada" if get_secret("GEMINI_API_KEY") else "ausente",
            "GROQ_API_KEY": "configurada" if get_secret("GROQ_API_KEY") else "ausente",
            "GEMINI_MODEL": GEMINI_MODEL,
            "GROQ_MODEL": GROQ_MODEL,
        },
        "observacao": (
            "A presença de uma chave não garante que ela seja válida. "
            "A validade é confirmada ao realizar uma chamada ao provedor."
        ),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await orquestrador(request.texto, request.tipo)


@app.post("/api/email/enviar")
async def email_enviar(request: EmailRequest):
    raise HTTPException(
        status_code=501,
        detail=(
            "Envio real de e-mail ainda não está integrado nesta versão. "
            "O endpoint foi mantido para compatibilidade, sem simular sucesso."
        ),
    )


@app.post("/api/email/analisar")
async def email_analisar(request: EmailRequest):
    raise HTTPException(
        status_code=501,
        detail=(
            "Análise de e-mails ainda não está integrada nesta versão. "
            "Será conectada ao serviço de e-mail e aos agentes em uma etapa posterior."
        ),
    )


# ---------------------------------------------------------------------------
# Interface web
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def raiz():
    if FRONTEND_FILE.is_file():
        try:
            return HTMLResponse(
                content=FRONTEND_FILE.read_text(encoding="utf-8")
            )
        except OSError:
            logger.exception("Não foi possível ler frontend/index.html.")

    return HTMLResponse(
        content=(
            "<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
            "<title>Nexuscore AI</title><body>"
            "<h1>Nexuscore AI — API online</h1>"
            "<p>A interface frontend/index.html ainda não foi encontrada.</p>"
            "</body></html>"
        ),
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Inicialização local
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
