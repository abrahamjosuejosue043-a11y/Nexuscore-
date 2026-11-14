import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.ai_brain import gerar_resposta, status_brain, gerar_voz
from backend.orchestrator import processar_mensagem, orchestrator

app = FastAPI(title="NEXUS CORE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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

@app.post("/api/voz")
async def voz(req: Request):
    dados = await req.json()
    quem = str(dados.get("quem", "ORION")).upper().strip()
    texto = str(dados.get("texto", ""))[:500]
    audio = gerar_voz(quem, texto)
    if audio:
        return Response(content=audio, media_type="audio/mpeg")
    return JSONResponse({"ok": False, "erro": "ElevenLabs sem voz"}, status_code=404)

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
