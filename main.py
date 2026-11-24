"""
NEXUSCORE AI — API CENTRAL
Arquivo: main.py (raiz do repositório)

Esta versão mantém as rotas principais do projeto e organiza:
- Inicialização do FastAPI e armazenamento SQLite
- Comunicação assíncrona com Gemini e Groq
- Seleção de perfil de agente e fallback entre provedores
- Histórico, ideias e rotas administrativas protegidas
- Integrações SMTP/IMAP sob demanda

IMPORTANTE:
- Os três perfis são instruções especializadas; ainda não existe colaboração multiagente encadeada.
- SMTP e IMAP dependem de credenciais válidas no ambiente do serviço.
- SQLite exige armazenamento persistente para conservar dados entre deploys.
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

from backend import storage

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
# Evita registrar URLs de requisição do Gemini, que carregam a chave na query string.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("nexuscore")

APP_NAME = "Nexuscore AI"
APP_VERSION = "1.1.0"

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

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
# Integração Groq (modelo configurado por variável de ambiente)
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
        storage.save_message("user", agent_type, text)
        storage.save_message("assistant", agent_type, cached["resposta"], cached.get("cerebro"))
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
            storage.save_message("user", agent_type, text)
            storage.save_message("assistant", agent_type, answer, provider_name)
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



@app.on_event("startup")
async def initialize_persistent_storage():
    storage.initialize()

@app.get("/api/saude")
async def saude():
    """Verificação básica, sem revelar valores ou nomes de segredos."""
    return {
        "status": "ok",
        "sistema": APP_NAME,
        "versao": APP_VERSION,
        "persistencia": "temporaria_no_plano_gratuito",
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




@app.get("/api/conversas")
async def listar_conversas(limit: int = 50, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    return {"items": storage.messages(limit)}

@app.get("/api/ideias")
async def listar_ideias(limit: int = 100, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    return {"items": storage.ideas(limit)}

@app.post("/api/ideias")
async def criar_ideia(request: dict, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    titulo = str(request.get("titulo", "")).strip()
    resumo = str(request.get("resumo", "")).strip()
    prioridade = str(request.get("prioridade", "media")).lower()
    if not titulo or not resumo or prioridade not in {"alta", "media", "baixa"}:
        raise HTTPException(status_code=422, detail="Informe título, resumo e prioridade alta, media ou baixa.")
    return {"id": storage.save_idea(titulo[:200], resumo[:10000], prioridade), "status": "salva"}


@app.get("/api/projetos")
async def listar_projetos(limit: int = 100, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    return {"items": storage.projects(limit)}

@app.post("/api/projetos")
async def criar_projeto(request: dict, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    titulo = str(request.get("titulo", "")).strip()
    resumo = str(request.get("resumo", "")).strip()
    if not titulo or not resumo:
        raise HTTPException(status_code=422, detail="Informe nome e descrição do projeto.")
    project_id = storage.save_project(titulo[:200], resumo[:10000])
    return {"id": project_id, "status": "criado"}

@app.patch("/api/projetos/{project_id}")
async def atualizar_projeto(project_id: int, request: dict, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    status = str(request.get("status", "")).strip().lower()
    if status not in {"planejado", "em_andamento", "concluido", "pausado"}:
        raise HTTPException(status_code=422, detail="Status inválido.")
    if not storage.update_project(project_id, status):
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return {"id": project_id, "status": status}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await orquestrador(request.texto, request.tipo)


@app.post("/api/email/enviar")
async def email_enviar(request: EmailRequest, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    import smtplib
    from email.message import EmailMessage
    recipient = request.destinatario.strip() or get_secret("EMAIL_DESTINATARIO")
    if not recipient or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise HTTPException(status_code=422, detail="Informe um destinatário válido em destinatario ou EMAIL_DESTINATARIO.")
    host, user, password = get_secret("SMTP_HOST"), get_secret("SMTP_USER"), get_secret("SMTP_PASSWORD")
    sender = get_secret("SMTP_FROM") or user
    if not all([host, user, password, sender]):
        raise HTTPException(status_code=503, detail="Configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD e SMTP_FROM no Render.")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = sender, recipient, request.assunto or "Mensagem do Nexuscore"
    message.set_content(request.texto)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=25) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
    except Exception as exc:
        logger.exception("Falha no envio SMTP")
        raise HTTPException(status_code=502, detail="Falha no envio SMTP. Verifique as configurações de e-mail.") from exc
    with storage.connection() as db:
        db.execute("INSERT INTO email_log(direction,recipient,subject,body,status) VALUES('outgoing',?,?,?,'sent')",
                   (recipient, request.assunto, request.texto))
    return {"status": "enviado", "destinatario": recipient}


@app.post("/api/email/analisar")
async def email_analisar(request: EmailRequest, x_admin_token: Optional[str] = Header(default=None)):
    require_admin_token(x_admin_token)
    result = await orquestrador(
        "Analise este e-mail. Gere título, resumo, oportunidade, prioridade e próxima ação.\n"
        + "Assunto: " + request.assunto + "\nConteúdo: " + request.texto,
        "diretoria",
    )
    idea_id = storage.save_idea(request.assunto or "E-mail analisado", result["resposta"], "media")
    return {"status": "analisado", "ideia_id": idea_id, "analise": result["resposta"]}


@app.get("/api/email/receber")
async def email_receber(
    limit: int = 10,
    x_admin_token: Optional[str] = Header(default=None),
):
    """Busca mensagens não lidas via IMAP e registra o conteúdo textual."""
    import imaplib
    import email
    from email.header import decode_header

    require_admin_token(x_admin_token)
    host = get_secret("IMAP_HOST")
    user = get_secret("IMAP_USER")
    password = get_secret("IMAP_PASSWORD")
    if not all([host, user, password]):
        raise HTTPException(status_code=503, detail="Configure IMAP_HOST, IMAP_USER e IMAP_PASSWORD no Render.")
    def decode_mime(value: str) -> str:
        pieces = []
        for part, encoding in decode_header(value or ""):
            pieces.append(part.decode(encoding or "utf-8", errors="replace") if isinstance(part, bytes) else part)
        return "".join(pieces)
    mailbox = None
    received = []
    try:
        mailbox = imaplib.IMAP4_SSL(host, int(os.getenv("IMAP_PORT", "993")))
        mailbox.login(user, password)
        mailbox.select(os.getenv("IMAP_FOLDER", "INBOX"))
        status, data = mailbox.search(None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("Falha ao consultar mensagens não lidas.")
        message_ids = (data[0].split() if data and data[0] else [])[-max(1, min(limit, 30)):]
        for message_id in message_ids:
            status, payload = mailbox.fetch(message_id, "(RFC822)")
            if status != "OK" or not payload or not payload[0]:
                continue
            message = email.message_from_bytes(payload[0][1])
            body = ""
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == "text/plain" and not part.get_filename():
                        raw = part.get_payload(decode=True) or b""
                        body += raw.decode(part.get_content_charset() or "utf-8", errors="replace")
            else:
                raw = message.get_payload(decode=True) or b""
                body = raw.decode(message.get_content_charset() or "utf-8", errors="replace")
            item = {"de": decode_mime(message.get("From", "")),
                    "assunto": decode_mime(message.get("Subject", "")),
                    "texto": body[:12000]}
            with storage.connection() as db:
                db.execute("INSERT INTO email_log(direction,sender,subject,body,status) VALUES('incoming',?,?,?,'received')",
                           (item["de"], item["assunto"], item["texto"]))
            received.append(item)
        return {"items": received, "count": len(received)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha na recepção IMAP")
        raise HTTPException(status_code=502, detail="Não foi possível receber e-mails. Verifique as configurações IMAP.") from exc
    finally:
        if mailbox is not None:
            try:
                mailbox.logout()
            except Exception:
                pass


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
