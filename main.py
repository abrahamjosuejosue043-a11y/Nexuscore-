import os
import uvicorn
import jwt
import datetime
import re
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from google import genai

app = FastAPI(title="Nexus Core v8.0 - Multidimensions & Voices")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.environ.get("OPENAI_API_KEY"))

USUARIO = "conselho@innovaxr.com"
SENHA = "password"
memoria_vetorial = []
chats_dept = {"engenharia": [], "marketing": [], "financeiro": [], "reuniao": []}
humano_assumiu = False

# 3 Identidades com comportamentos e parâmetros distintos
AGENTES = {
    "engenharia": {
        "nome": "Atlas",
        "voz": "pt-BR-Neural2-B",  # Tom mais grave, técnico e objetivo
        "temperamento": "Analítico, focado em lógica, arquitetura de sistemas, robustez e otimização de código."
    },
    "marketing": {
        "nome": "Lyra",
        "voz": "pt-BR-Neural2-A",  # Tom dinâmico e expressivo
        "temperamento": "Criativo, focado em expansão de marca, engajamento, psicologia do consumidor e tendências."
    },
    "financeiro": {
        "nome": "Chronos",
        "voz": "pt-BR-Neural2-C",  # Tom sóbrio, prudente e calculista
        "temperamento": "Estratégico, focado em mitigação de riscos,ROI, fluxo de caixa e segurança patrimonial."
    }
}

def token_email():
    agora = datetime.datetime.now(datetime.timezone.utc)
    return jwt.encode({"sub": "email", "exp": agora + datetime.timedelta(hours=1)}, "secreto", algorithm="HS256")

def verificar(req: Request):
    auth = req.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    try:
        return jwt.decode(auth.replace("Bearer ", ""), "secreto", algorithms=["HS256"])
    except:
        return None

def salvar_memoria(brain, texto_dentro):
    palavras = set(re.findall(r'\b\w{4,}\b', texto_dentro.lower()))
    ignorar = {'para', 'como', 'renda', 'novo', 'criar', 'codigo', 'script', 'fazer', 'mais'}
    for p in (palavras - ignorar):
        if any(p == i['conceito'] for i in brain):
            for i in brain:
                if i['conceito'] == p: i['relevancia'] += 1
        elif len(brain) < 30:
            brain.append({'conceito': p, 'relevancia': 1, 'sinapses': []})

@app.post("/auth/login")
async def login(request: Request):
    data = await request.json()
    if data.get("email") == USUARIO and data.get("senha") == SENHA:
        return {"status": "ok", "token": token_email()}
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/app/executar")
async def executar_tarefa(request: Request):
    token_data = verificar(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    data = await request.json()
    comando = data.get("comando", "").strip()
    dept = data.get("dept", "engenharia").lower()
    
    if not comando:
        return {"status": "erro", "resposta": "Comando vazio."}
        
    agente = AGENTES.get(dept, AGENTES["engenharia"])
    
    prompt = f"""
    Você é {agente['nome']}, um agente autônomo do Nexus Core.
    Seu perfil comportamental: {agente['temperamento']}
    Departamento atual: {dept}.
    Comando recebido do usuário: '{comando}'.
    Responda mantendo rigorosamente sua identidade, voz característica e foco estratégico.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        resposta_ia = response.text
    except Exception as e:
        return {"status": "erro", "resposta": f"Erro na API Gemini: {str(e)}"}
        
    if dept in chats_dept:
        chats_dept[dept].append({"role": "user", "parts": [{"text": comando}]})
        chats_dept[dept].append({"role": "model", "parts": [{"text": resposta_ia}]})
        
    salvar_memoria(memoria_vetorial, comando + " " + resposta_ia)
    
    return {
        "status": "sucesso", 
        "resposta": resposta_ia, 
        "agente": agente['nome'], 
        "voz": agente['voz']
    }

@app.post("/app/reuniao_autonoma")
async def reuniao_autonoma(request: Request):
    """Simula a mesa redonda onde os 3 agentes debatem livremente entre si sobre um tema proposto."""
    token_data = verificar(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    data = await request.json()
    topico = data.get("topico", "Estratégia geral e expansão do ecossistema Nexus").strip()
    
    prompt_debate = f"""
    Simule uma reunião em tempo real entre os 3 agentes do Nexus Core sobre o tópico: '{topico}'.
    1. Atlas (Engenharia): Foca na viabilidade técnica e arquitetura.
    2. Lyra (Marketing): Foca na experiência e atração de usuários.
    3. Chronos (Financeiro): Foca em custos, sustentabilidade e prazos.
    Faça um diálogo fluído, espontâneo e em formato de conversação interativa onde eles debatem entre si e chegam a uma conclusão conjunta para o usuário.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_debate,
        )
        debate_texto = response.text
    except Exception as e:
        return {"status": "erro", "resposta": f"Erro na simulação: {str(e)}"}
        
    chats_dept["reuniao"].append({"topico": topico, "debate": debate_texto})
    
    return {
        "status": "sucesso",
        "debate": debate_texto,
        "participantes": [AGENTES["engenharia"], AGENTES["marketing"], AGENTES["financeiro"]]
    }

@app.get("/app/memoria")
async def obter_memoria(request: Request):
    token_data = verificar(request)
    if not token_data: raise HTTPException(status_code=401, detail="Unauthorized")
    return {"memoria": memoria_vetorial}

@app.post("/app/debriefing")
async def debriefing(request: Request):
    token_data = verificar(request)
    if not token_data: raise HTTPException(status_code=401, detail="Unauthorized")
    status_str = f"nexus_core: \"v8.0 ONLINE\", \"memoria\": {len(memoria_vetorial)}, \"agentes\": 3, \"status\": \"200 OK\""
    return HTMLResponse(content=f"<html><body><pre>{status_str}</pre></body></html>")

@app.post("/app/assumir")
async def assumir_controle(request: Request):
    global humano_assumiu
    token_data = verificar(request)
    if not token_data: raise HTTPException(status_code=401, detail="Unauthorized")
    humano_assumiu = True
    return {"status": "humano_no_controle"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
