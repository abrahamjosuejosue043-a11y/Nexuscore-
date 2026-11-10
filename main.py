import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
from backend.orchestrator import OrquestradorNexusV4
from backend.email_service import EmailService
app = FastAPI(title="Nexus Core V4 - Innova XR")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
# Frontend fica na pasta frontend
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")
orc = OrquestradorNexusV4()
email_svc = EmailService()
class Pergunta(BaseModel):
    pergunta: str
    destino: str = "todos"
class EmailConfig(BaseModel):
    email: str
    nome: str = "CEO Innova XR"
class Relatorio(BaseModel):
    email: str = ""
    conteudo: str = ""
@app.get("/")
def home():
    return {"nexus_core": "V4 FINAL - Futuristic Workspace ON", "gemini": bool(os.getenv("GEMINI_API_KEY")), "meta": bool(os.getenv("META_API_KEY")), "departamentos": ["Lab - Meta AI", "Marketing - Gemini", "Diretoria - Gemini"]}
@app.get("/health")
def health():
    return orc.health()
@app.post("/perguntar")
def perguntar(dados: Pergunta):
    return orc.reuniao(str(dados.pergunta), str(dados.destino))
@app.post("/config/email")
def config_email(dados: EmailConfig):
    email = str(dados.email).strip()
    nome = str(dados.nome or "CEO")
    email_svc.cadastrar(email, nome)
    return {"ok": True, "mensagem": "E-mail cadastrado no Nexus Core: " + email, "email": email}
@app.post("/relatorio/email")
def relatorio(dados: Relatorio):
    email = str(dados.email or email_svc.email_atual or "").strip()
    conteudo = str(dados.conteudo or "")
    if not email:
        return {"ok": False, "modo": "erro", "mensagem": "Cadastre seu e-mail primeiro na aba E-mail / Config"}
    return email_svc.enviar_relatorio(email, conteudo)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
