# NEXUS CORE V11 - ELEVENLABS GATEWAY + NEBULOSA + DIRECIONADO TRAVADO
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
from backend.orchestrator import OrquestradorNexusV4
from backend.email_service import EmailService
app = FastAPI(title="Nexus Core V11 - Innova XR")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
orc = OrquestradorNexusV4()
email_svc = EmailService()
class Pergunta(BaseModel):
    pergunta: str
    destino: str = "todos"
    projeto: str = "Geral"
class EmailConfig(BaseModel):
    email: str
    nome: str = "CEO Innova XR"
class Relatorio(BaseModel):
    email: str = ""
    conteudo: str = ""
class VozFalar(BaseModel):
    texto: str
    quem: str = "lab"
    # quem: lab=FORJA, marketing=LIA, diretoria=ORION
class LabCriar(BaseModel):
    pergunta: str
    tipo: str = "codigo"
    projeto: str = "Geral"
@app.get("/voz/diagnostico")
def voz_diagnostico():
    # Mostra o motivo exato: chave presente? tamanho? backend V11? Sem expor a chave.
    d = orc.elevenlabs.diagnostico()
    d["rota"] = "/voz/diagnostico OK - backend V11 novo"
    return d
@app.get("/voz/config")
def voz_config():
    # Frontend pergunta: ElevenLabs está ligado? Sem expor a chave.
    return orc.elevenlabs.config()
@app.post("/voz/falar")
def voz_falar(dados: VozFalar):
    # GATEWAY: frontend manda texto, backend manda para ElevenLabs com a chave secreta, devolve MP3.
    audio = orc.elevenlabs.gerar_audio(str(dados.texto or ""), str(dados.quem or "lab"))
    if not audio:
        diag = orc.elevenlabs.diagnostico()
        return {"ok": False, "mensagem": "ElevenLabs indisponível - usando voz do navegador.", "motivo_detalhado": diag.get("motivo", ""), "diagnostico": diag}
    return Response(content=audio, media_type="audio/mpeg")
@app.post("/voz/teste")
def voz_teste():
    # Teste rápido: 1 frase do ORION para confirmar que a chave funciona
    audio = orc.elevenlabs.gerar_audio("Olá Senhor Josué, aqui é o ORION, voz ElevenLabs conectada e pronta.", "diretoria")
    if not audio: return {"ok": False, "mensagem": "ElevenLabs não respondeu. Confira a chave e o crédito em elevenlabs.io"}
    return Response(content=audio, media_type="audio/mpeg")
@app.get("/health")
def health(): return orc.health()
@app.get("/api/health")
def health2(): return orc.health()
@app.post("/perguntar")
def perguntar(dados: Pergunta):
    # ANTES: não recebia projeto, perdia o contexto. AGORA: recebe projeto.
    return orc.reuniao(str(dados.pergunta), str(dados.destino), str(dados.projeto or "Geral"))
@app.post("/lab/criar")
def lab_criar(dados: LabCriar):
    # Lab igual ao app Meta: codigo, imagem, texto - sempre responde
    return orc.lab_criar(str(dados.pergunta), str(dados.tipo or "codigo"), str(dados.projeto or "Geral"))
@app.post("/config/email")
def config_email(dados: EmailConfig):
    email = str(dados.email).strip(); nome = str(dados.nome or "CEO")
    email_svc.cadastrar(email, nome)
    return {"ok": True, "mensagem": "E-mail cadastrado no Nexus Core: " + email, "email": email}
@app.post("/relatorio/email")
def relatorio(dados: Relatorio):
    email = str(dados.email or email_svc.email_atual or "").strip()
    conteudo = str(dados.conteudo or "")
    if not email: return {"ok": False, "modo": "erro", "mensagem": "Cadastre seu e-mail primeiro na aba E-mail / Config"}
    return email_svc.enviar_relatorio(email, conteudo)
# Frontend na RAIZ: antes / retornava JSON e /app era o frontend, por isso no Render aparecia tela estranha. Agora / abre o app.
@app.get("/")
def home():
    idx = os.path.join(frontend_path, "index.html")
    if os.path.exists(idx): return FileResponse(idx)
    return {"nexus_core": "V11 - Innova XR", "gemini": bool(os.getenv("GEMINI_API_KEY")), "meta": bool(os.getenv("META_API_KEY"))}
# CORRIGIDO V11: /app NÃO abre mais pasta antiga. /app redireciona para / (entrada certa).
# Antes, /app abria a pasta frontend direto e mostrava versão velha em cache.
@app.get("/app")
def app_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
