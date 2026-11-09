import os
import uvicorn
import jwt
import time
import datetime
import random
import re
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from openai import OpenAI

app = FastAPI(title="Nexus Core v7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

USUARIO = "conselho@innovaxr.com"
SENHA = "password"
memoria_vetorial = []
chats_dept = {"engenharia": [], "marketing": [], "financeiro": []}
humano_assumiu = False

def token_email():
    agora = datetime.datetime.utcnow()
    return jwt.encode({"sub": "email", "exp": agora + datetime.timedelta(hours=1)}, "secret", algorithm="HS256")

def verificar(req: Request):
    auth = req.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    try:
        return jwt.decode(auth.replace("Bearer ", ""), "secret", algorithms=["HS256"])
    except:
        return None

def salvar_memoria(brain, texto, dept="geral"):
    palavras = set(re.findall(r'\w+', texto.lower()))
    memoria_vetorial.append({"brain": brain, "texto": texto, "dept": dept, "palavras": palavras})
    return True

def recuperar_memoria(query, dept="geral"):
    palavras_query = set(re.findall(r'\w+', query.lower()))
    melhor = None
    max_score = 0
    for mem in memoria_vetorial:
        if mem["dept"] == dept or mem["dept"] == "geral":
            score = len(palavras_query.intersection(mem["palavras"]))
            if score > max_score:
                max_score = score
                melhor = mem
    return melhor["texto"] if melhor else None

ESTILOS = {
    "moderador": "Seja analítico, equilibrado e focado na eficácia sistêmica.",
    "inovador": "Foque em soluções disruptivas, IA e automação avançada.",
    "estrategista": "Priorize viabilidade de mercado, ROI e escalabilidade."
}

def gerar_resposta(brain, tema, contexto_anterior=""):
    base = random.choice(list(ESTILOS.values()))
    texto = base + f" (Tema: {tema})"
    if contexto_anterior:
        texto += f" (Respondendo a: {contexto_anterior})"
    return texto

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NEXUS CORE v7.0</title>
<style>
body { background: #0f172a; color: #f8fafc; font-family: sans-serif; margin: 0; padding: 15px; }
.card { background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
h2, h3 { margin-top: 0; color: #38bdf8; }
input, button { padding: 10px; border-radius: 5px; border: 1px solid #475569; width: 100%; box-sizing: border-box; margin-top: 5px; }
input { background: #334155; color: #fff; }
button { cursor: pointer; font-weight: bold; }
.azul { background: #0284c7; color: #fff; border: none; }
.verde { background: #16a34a; color: #fff; border: none; }
.cinza { background: #475569; color: #fff; border: none; }
.chat { background: #0f172a; border: 1px solid #334155; padding: 10px; height: 150px; overflow-y: scroll; border-radius: 5px; font-size: 14px; margin-top: 10px; }
.msg { margin-bottom: 8px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }
</style>
</head>
<body>

<div class="card" id="loginBox">
<h3>🔐 Autenticação</h3>
<input id="email" value="conselho@innovaxr.com" placeholder="E-mail">
<input id="senha" type="password" value="123456" placeholder="Senha">
<button class="azul" onclick="login()">Entrar no Nexus</button>
</div>

<div class="card" id="painel" style="display:none;">
<h3>🧠 Conselho de IAs</h3>
<input id="tema" value="Como melhorar nosso ecossistema">
<button class="verde" onclick="iniciarDebate()">▶ Iniciar Debate Autônomo</button>
<div class="chat" id="chatGeral"></div>

<h3 style="margin-top:20px;">🏢 Departamentos & Execução de Tarefas</h3>
<div style="display:flex; gap:5px; margin-bottom:10px;">
<button class="cinza" onclick="abrirDept('engenharia')">🛠 Engenharia</button>
<button class="cinza" onclick="abrirDept('marketing')">📢 Marketing</button>
<button class="cinza" onclick="abrirDept('financeiro')">💰 Financeiro</button>
</div>

<p id="lblDept" style="font-weight:bold; color:#38bdf8;">Departamento: engenharia</p>
<div class="chat" id="chatDept"></div>
<input id="txtComando" placeholder="Digite comando ou peça código...">
<button class="azul" onclick="enviarDept()">Enviar p/ Departamento</button>
<button class="verde" onclick="executarTarefa()">⚡ Executar Tarefa + Gerar Código</button>

<h3 style="margin-top:20px;">🗣️ Voz & E-mail</h3>
<button class="cinza" onclick="ditar()">🎙️ Ditar Comando por Voz (STT)</button>
<button class="cinza" onclick="ouvir()">🔊 Ouvir Última Fala (TTS)</button>
<input id="txtEmail" value="conselho@innovaxr.com">
<button class="verde" onclick="enviarEmail()">✉️ Enviar Relatório por E-mail</button>
</div>

<script>
let TOKEN = "";
let DEPT_ATUAL = "engenharia";

async function login() {
    let r = await fetch("/auth/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email: document.getElementById("email").value, senha: document.getElementById("senha").value})
    });
    let j = await r.json();
    if(j.access_token) {
        TOKEN = j.access_token;
        document.getElementById("loginBox").style.display = "none";
        document.getElementById("painel").style.display = "block";
        alert("Logado com sucesso!");
        carregarChats();
    } else {
        alert("Erro no login");
    }
}

function abrirDept(d) {
    DEPT_ATUAL = d;
    document.getElementById("lblDept").innerText = "Departamento: " + d;
    carregarChats();
}

async function carregarChats() {
    let r = await fetch("/departamentos/dept/chat?dept=" + DEPT_ATUAL, {headers: {"Authorization": "Bearer " + TOKEN}});
    let j = await r.json();
    let box = document.getElementById("chatDept");
    box.innerHTML = "";
    j.mensagens.forEach(m => {
        box.innerHTML += `<div class="msg"><b>${m.autor}:</b> ${m.msg}</div>`;
    });
    box.scrollTop = box.scrollHeight;
}

async function enviarDept() {
    let msg = document.getElementById("txtComando").value;
    await fetch("/departamentos/dept/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
        body: JSON.stringify({dept: DEPT_ATUAL, msg: msg})
    });
    document.getElementById("txtComando").value = "";
    carregarChats();
}

async function executarTarefa() {
    let msg = document.getElementById("txtComando").value;
    let r = await fetch("/tarefas/executar", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
        body: JSON.stringify({dept: DEPT_ATUAL, comando: msg})
    });
    let j = await r.json();
    alert("Tarefa executada!");
    carregarChats();
}

async function iniciarDebate() {
    let tema = document.getElementById("tema").value;
    let r = await fetch("/sala/debate", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
        body: JSON.stringify({tema: tema})
    });
    let j = await r.json();
    let box = document.getElementById("chatGeral");
    box.innerHTML = "";
    j.debate.forEach(d => {
        box.innerHTML += `<div class="msg"><b>${d.brain}:</b> ${d.texto}</div>`;
    });
}

function ditar() {
    let rec = new webkitSpeechRecognition();
    rec.lang = "pt-BR";
    rec.onresult = e => { document.getElementById("txtComando").value = e.results[0][0].transcript; };
    rec.start();
}

function ouvir() {
    let box = document.getElementById("chatDept");
    let ultimo = box.innerText.split("\\n").pop() || "Nenhuma fala recente";
    let u = new SpeechSynthesisUtterance(ultimo);
    u.lang = "pt-BR";
    speechSynthesis.speak(u);
}

async function enviarEmail() {
    let email = document.getElementById("txtEmail").value;
    await fetch("/relatorio/email", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
        body: JSON.stringify({email: email})
    });
    alert("Relatório enviado para " + email);
}
</script>
</body>
</html>
"""

@app.post("/auth/login")
async def login(request: Request):
    data = await request.json()
    if data.get("email") == USUARIO and data.get("senha") == SENHA:
        return {"access_token": token_email()}
    return Response(status_code=401)

@app.post("/sala/debate")
async def debate(request: Request):
    if not verificar(request): return Response(status_code=401)
    data = await request.json()
    tema = data.get("tema", "Inovação")
    
    debate_res = []
    brains = ["moderador", "inovador", "estrategista"]
    contexto = ""
    for b in brains:
        prompt = f"Atue como {b}. Comente sobre o tema: {tema}. Contexto anterior: {contexto}"
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            texto = response.choices[0].message.content
        except Exception as e:
            texto = gerar_resposta(b, tema, contexto)
            
        debate_res.append({"brain": b, "texto": texto})
        contexto = texto
    return {"debate": debate_res}

@app.get("/departamentos/dept/chat")
async def get_chat(dept: str, request: Request):
    if not verificar(request): return Response(status_code=401)
    return {"departamento": dept, "mensagens": chats_dept.get(dept, [])}

@app.post("/departamentos/dept/chat")
async def post_chat(request: Request):
    if not verificar(request): return Response(status_code=401)
    data = await request.json()
    dept = data.get("dept", "engenharia")
    msg = data.get("msg", "")
    salvar_memoria("usuario", msg, dept)
    chats_dept[dept].append({"autor": "usuário", "msg": msg})
    return {"ok": True, "resposta": "Recebido"}

@app.post("/tarefas/executar")
async def executar_tarefa(request: Request):
    if not verificar(request): return Response(status_code=401)
    data = await request.json()
    dept = data.get("dept", "engenharia")
    comando = data.get("comando", "Criar script básico")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Você é a IA do departamento de {dept}. Responda estritamente gerando o código ou artefato técnico solicitado."},
                {"role": "user", "content": comando}
            ]
        )
        artefato = response.choices[0].message.content
    except Exception as e:
        artefato = f"# Erro ao conectar com a API OpenAI: {str(e).lower()}"

    chats_dept[dept].append({"autor": dept.upper(), "msg": artefato})
    return {"departamento": dept, "artefato": artefato}

@app.post("/relatorio/email")
async def relatorio_email(request: Request):
    if not verificar(request): return Response(status_code=401)
    data = await request.json()
    return {"enviado_para": data.get("email")}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
