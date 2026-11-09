from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
from google import genai
from google.genai import types

app = FastAPI(title="Nexus Core", version="4.0")

# Inicialização do cliente Google GenAI utilizando a chave de ambiente GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Definição das personas dos agentes
AGENTES = {
    "engenharia": {
        "nome": "Atlas",
        "perfil": "Engenheiro sênior, focado em arquitetura limpa, escalabilidade, performance e robustez de código.",
    },
    "marketing": {
        "nome": "Lyra",
        "perfil": "Estrategista de marketing, focada em engajamento, conversão, posicionamento de marca e campanhas virais.",
    },
    "financeiro": {
        "nome": "Chronos",
        "perfil": "Analista financeiro e de operações, focado em ROI, eficiência de custos, mitigação de riscos e viabilidade.",
    }
}

class TarefaRequest(BaseModel):
    comando: str
    departamento: str

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Nexus Core - Autenticação</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); width: 100%; max-width: 400px; }
            h2 { margin-bottom: 1.5rem; color: #38bdf8; text-align: center; }
            .input-group { margin-bottom: 1rem; }
            label { display: block; margin-bottom: 0.5rem; font-size: 0.875rem; }
            input { width: 100%; padding: 0.75rem; border: 1px solid #334155; border-radius: 4px; background: #0f172a; color: #fff; box-sizing: border-box; }
            button { width: 100%; padding: 0.75rem; background: #38bdf8; border: none; border-radius: 4px; color: #0f172a; font-weight: bold; cursor: pointer; margin-top: 1rem; }
            button:hover { background: #0ea5e9; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Nexus Core - Autenticação</h2>
            <form action="/auth/login" method="POST">
                <div class="input-group">
                    <label>E-mail</label>
                    <input type="email" name="username" value="conselho@innovaxr.com" required>
                </div>
                <div class="input-group">
                    <label>Senha</label>
                    <input type="password" name="password" value="password" required>
                </div>
                <button type="submit">Entrar no Nexus</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.get("/auth/login", response_class=HTMLResponse)
async def login_get():
    return await home()

@app.post("/auth/login")
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    if username == "conselho@innovaxr.com" and password == "password":
        return {
            "status": "success", 
            "message": "Autenticado com sucesso",
            "token": "jwt-token-simulado-nexus-core"
        }
    raise HTTPException(status_code=401, detail="Credenciais inválidas")

@app.post("/app/executar")
async def executar_tarefa(dados: TarefaRequest):
    dept = dados.departamento.lower()
    if dept not in AGENTES:
        raise HTTPException(status_code=400, detail="Departamento inválido. Escolha entre: engenharia, marketing, financeiro.")
    
    agente = AGENTES[dept]
    prompt = f"Você é {agente['nome']}, atuando como {agente['perfil']}. Responda à seguinte solicitação mantendo estritamente a sua persona: {dados.comando}"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {
            "status": "ok",
            "departamento": dept,
            "agente": agente['nome'],
            "resposta": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
