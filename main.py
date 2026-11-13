import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
load_dotenv()

from backend.orchestrator import orchestrator
from backend.email_service import enviar_relatorio_para_voce, verificar_ideias_novas

app = FastAPI(title="NEXUS CORE - Innova XR")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Chaves - todas vêm do Render, nenhuma fica no GitHub
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", "")
META_KEY = os.getenv("META_AI_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
VOICES = {
    "ORION": os.getenv("ELEVENLABS_VOICE_ORION", "21m00Tcm4TlvDq8ikWAM"),
    "FORJA": os.getenv("ELEVENLABS_VOICE_FORJA", "21m00Tcm4TlvDq8ikWAM"),
    "LIA": os.getenv("ELEVENLABS_VOICE_LIA", "21m00Tcm4TlvDq8ikWAM"),
}

class VoiceIn(BaseModel):
    quem: str = "ORION"
    texto: str = ""
class ChatIn(BaseModel):
    quem: str = "ORION"
    pergunta: str = ""
class TaskIn(BaseModel):
    quem: str = "ORION"
    titulo: str = ""
    status: str = "todo"
class MoveIn(BaseModel):
    id: int = 0
    status: str = "todo"
class EmailIdeia(BaseModel):
    assunto: str = ""
    texto: str = ""

@app.get("/api/health")
async def health():
    return {"ok": True, "meta": bool(META_KEY), "gemini_backup": bool(GEMINI_KEY), "elevenlabs": bool(ELEVEN_KEY), "versao": "12.0"}

@app.get("/api/status")
async def status():
    return {"meta_online": bool(META_KEY), "gemini_online": bool(GEMINI_KEY), "voz_online": bool(ELEVEN_KEY), "modo": "Meta principal, Gemini reserva"}

@app.get("/api/project")
async def get_project():
    return {"tarefas": orchestrator.listar_tarefas()}

@app.post("/api/project/task")
async def add_task(body: TaskIn):
    t = orchestrator.adicionar_tarefa(body.quem, body.titulo, body.status)
    return {"ok": True, "tarefa": t, "tarefas": orchestrator.listar_tarefas()}

@app.post("/api/project/move")
async def move_task(body: MoveIn):
    t = orchestrator.mover_tarefa(body.id, body.status)
    return {"ok": True, "tarefa": t}

@app.post("/api/chat")
async def chat(body: ChatIn):
    # Tenta usar o cérebro Meta/Gemini, se falhar usa resposta rápida
    try:
        resposta = await orchestrator.responder_async(body.quem, body.pergunta)
    except:
        resposta = orchestrator.responder(body.quem, body.pergunta)
    return {"quem": body.quem.upper(), "resposta": resposta}

@app.post("/api/voice")
async def voice(body: VoiceIn):
    if not ELEVEN_KEY:
        return JSONResponse({"erro": "ElevenLabs não configurada"}, status_code=503)
    voice_id = VOICES.get(body.quem.upper(), VOICES["ORION"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {"text": body.texto, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.45, "similarity_boost": 0.75}}
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            return JSONResponse({"erro": "ElevenLabs falhou"}, status_code=r.status_code)
        return Response(content=r.content, media_type="audio/mpeg")

# E-mail: você manda ideia, cai pro Orion primeiro
@app.post("/api/email/ideia")
async def receber_ideia(body: EmailIdeia):
    # Orion recebe primeiro, depois distribui
    texto_orion = f"Ideia nova do Senhor Josué: {body.assunto} - {body.texto}. Vou passar para Forja e Lia."
    # Salva como tarefa do Orion
    orchestrator.adicionar_tarefa("ORION", f"Ideia: {body.assunto} - {body.texto[:80]}", "todo")
    return {"ok": True, "para": "ORION primeiro", "resposta": texto_orion, "proximo": "Forja e 【entity-Lia¦canonical_name=Lia】 vão receber em seguida"}

@app.get("/api/email/ideias-novas")
async def ler_ideias():
    ideias = verificar_ideias_novas()
    for ideia in ideias:
        orchestrator.adicionar_tarefa("ORION", f"E-mail ideia: {ideia['assunto']}", "todo")
    return {"ok": True, "quantidade": len(ideias), "ideias": ideias, "fluxo": "Orion recebeu primeiro, depois passa pro time"}

@app.post("/api/email/relatorio")
async def enviar_relatorio():
    tarefas = orchestrator.listar_tarefas()
    feitas = len([t for t in tarefas if t["status"] == "feito"])
    resumo = f"Projeto: {feitas} de {len(tarefas)} prontas.\n"
    for t in tarefas:
        resumo += f"- [{t['quem']}] {t['titulo']} - {t['status']}\n"
    ok = enviar_relatorio_para_voce(resumo)
    return {"ok": ok, "mensagem": "Relatório enviado pro seu e-mail pessoal" if ok else "E-mail não configurado ainda - faça o Passo 2"}

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
@app.get("/manifest.json")
async def manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"))
@app.get("/sw.js")
async def sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
@app.get("/{path:path}")
async def fallback(path: str):
    if path.startswith("api/"):
        return JSONResponse({"erro": "rota não encontrada"}, status_code=404)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
