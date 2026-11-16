import os
import base64
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Imports com fallback para nao derrubar o app se um arquivo falhar
try:
    from backend.ai_brain import gerar_resposta, status_brain, gerar_voz
except Exception as e:
    def status_brain():
        return {"meta": False, "gemini": False, "elevenlabs": False, "ultimo_erro_groq": "Erro import ai_brain: " + str(e)}
    def gerar_resposta(quem, msg):
        return {"quem": quem, "texto": "Erro no cerebro: " + str(e), "fonte": "erro"}
    def gerar_voz(quem, texto):
        return None

try:
    from backend.orchestrator import processar_mensagem, orchestrator
except Exception as e:
    def processar_mensagem(quem="ORION", mensagem=None, **kw):
        if mensagem is None:
            mensagem = quem
            quem = "ORION"
        return gerar_resposta(quem, mensagem)
    class _Fake:
        fila = []
        vez_de = "ORION"
        def pedir_palavra(self, quem):
            return {"fila": [], "vez_de": "ORION"}
    orchestrator = _Fake()

def carregar_index():
    for caminho in ["frontend/index.html", "index.html", "frontend/index.htm"]:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>NEXUS CORE - index.html nao encontrado</h1>"

@app.get("/", response_class=HTMLResponse)
async def home():
    return carregar_index()

@app.get("/api/status")
async def api_status():
    s = status_brain()
    s["fila"] = getattr(orchestrator, "fila", [])
    s["vez_de"] = getattr(orchestrator, "vez_de", "ORION")
    return s

@app.get("/api/health")
async def api_health():
    return await api_status()

@app.post("/api/chat")
async def api_chat(req: Request):
    dados = await req.json()
    quem = dados.get("quem") or dados.get("personagem") or "ORION"
    mensagem = dados.get("mensagem") or dados.get("texto") or dados.get("message") or ""
    if not mensagem:
        return {"quem": quem, "texto": "Senhor Josue, mande uma mensagem.", "fonte": "aviso"}
    return processar_mensagem(quem, mensagem)

@app.post("/api/voz")
async def api_voz(req: Request):
    dados = await req.json()
    quem = dados.get("quem") or "ORION"
    texto = dados.get("texto") or dados.get("mensagem") or ""
    if not texto:
        return {"audio_base64": None, "usar_navegador": True}
    audio = gerar_voz(quem, texto)
    if audio:
        b64 = base64.b64encode(audio).decode("utf-8")
        return {"audio_base64": b64, "usar_navegador": False, "quem": quem}
    # Sem audio do ElevenLabs, o navegador fala sozinho - voz nunca fica muda
    return {"audio_base64": None, "usar_navegador": True, "quem": quem, "texto": texto}

@app.post("/api/reuniao/pedir-palavra")
async def api_pedir(req: Request):
    dados = await req.json()
    quem = dados.get("quem") or "FORJA"
    return orchestrator.pedir_palavra(quem)

@app.get("/api/email/ideias-novas")
async def api_email():
    try:
        from backend.email_service import listar_ideias_novas
        return listar_ideias_novas()
    except Exception as e:
        return {"quantidade": 0, "ideias": [], "erro": str(e)}


@app.post("/api/email/enviar")
async def api_email_enviar(req: Request):
    dados = await req.json()
    destino = dados.get("para") or dados.get("destino") or ""
    assunto = dados.get("assunto") or "NEXUS CORE - Relatorio"
    texto = dados.get("texto") or dados.get("mensagem") or ""
    try:
        from backend.email_service import enviar_email
        return enviar_email(destino, assunto, texto)
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.get("/api/elevenlabs/teste")
async def api_eleven_teste():
    # Mostra o erro real do ElevenLabs para diagnosticar
    try:
        from backend.ai_brain import status_brain, gerar_voz
        s = status_brain()
        # Tenta gerar 1 audio curto para ver o erro
        audio = gerar_voz("ORION", "Teste de voz Nexus Core.")
        if audio:
            return {"ok": True, "mensagem": "ElevenLabs LIGADO - audio gerado", "status": s}
        return {"ok": False, "mensagem": "ElevenLabs falhou - veja ultimo_erro_elevenlabs", "status": s}
    except Exception as e:
        return {"ok": False, "erro": str(e)}
