import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.ai_brain import gerar_resposta, status_brain
from backend.orchestrator import processar_mensagem, orchestrator

app = FastAPI(title="NEXUS CORE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    s = status_brain()
    return {"meta": s["meta"], "gemini": s["gemini"], "elevenlabs": s["elevenlabs"]}

@app.post("/api/chat")
async def chat(req: Request):
    dados = await req.json()
    quem = str(dados.get("quem", "ORION")).upper().strip()
    mensagem = str(dados.get("mensagem", ""))
    resultado = processar_mensagem(quem, mensagem)
    return JSONResponse(resultado)

@app.post("/api/reuniao/iniciar")
async def reuniao_iniciar(req: Request):
    dados = await req.json()
    mensagem = dados.get("mensagem", "inicia reuniao")
    resultado = processar_mensagem("ORION", mensagem)
    return JSONResponse(resultado)

@app.post("/api/reuniao/pedir-palavra")
async def pedir_palavra(req: Request):
    dados = await req.json()
    quem = str(dados.get("quem", "FORJA")).upper().strip()
    resultado = orchestrator.pedir_palavra(quem, "pedir a palavra")
    return JSONResponse(resultado)

@app.get("/api/email/ideias-novas")
def ideias_novas():
    try:
        from backend.email_service import buscar_ideias_novas
        ideias = buscar_ideias_novas()
        return {"ok": True, "quantidade": len(ideias), "ideias": ideias}
    except Exception as e:
        return {"ok": False, "quantidade": 0, "erro": str(e)}

@app.get("/")
def home():
    caminho = os.path.join("frontend", "index.html")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>NEXUS CORE Online</h1>")

@app.get("/api/status")
def status():
    return health()
