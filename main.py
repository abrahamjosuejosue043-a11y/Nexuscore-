import uvicorn, jwt, time, datetime, random, re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Nexus Core v7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

USUARIO="conselho@innovaxr.com"; SENHA="nexus2026"; CODIGO_2FA="123456"; SECRET="nexus-secret-2026"
memoria_vetorial=[]
chats_dept={ "engenharia":[], "marketing":[], "financeiro":[], "juridico":[], "operacoes":[] }
humano_assumiu=False

def token(email):
    agora=datetime.datetime.utcnow()
    return jwt.encode({"sub":email,"exp":agora+datetime.timedelta(hours=2),"iat":agora}, SECRET, algorithm="HS256")

def verificar(req: Request):
    auth=req.headers.get("authorization","")
    if not auth.startswith("Bearer "): return None
    try: return jwt.decode(auth.replace("Bearer ",""), SECRET, algorithms=["HS256"]).get("sub")
    except: return None

def salvar_memoria(brain, texto, dept="geral", tags=[]):
    palavras=set(re.findall(r'\w+', texto.lower()))
    memoria_vetorial.append({"brain":brain,"content":texto,"dept":dept,"palavras":list(palavras),"hora":time.strftime("%H:%M:%S"),"tags":tags})
    return True

def buscar_memoria(query, top=5):
    q=set(re.findall(r'\w+', query.lower()))
    scored=[]
    for m in memoria_vetorial:
        overlap=len(q.intersection(set(m["palavras"])))
        if overlap>0: scored.append((overlap,m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _,m in scored[:top]]

def moderar(texto):
    proibido=["xingamento","ofensa","desrespeito"]
    baixo=texto.lower()
    for p in proibido:
        if p in baixo: return False, "Moderador bloqueou: tom desrespeitoso."
    return True, "Aprovado"

ESTILOS={
 "meta": ["Visão estratégica: {t} exige posicionamento claro.", "Como META, alinhando estratégia e execução para {t}."],
 "gpt": ["Como GPT, analisando tecnicamente {t}: proponho prototipar antes de escalar.", "Do ponto de vista técnico, {t} exige validação de escopo."],
 "claude": ["Como Claude, olhando com cuidado para {t}: sugiro ajustar o tom e validar dados."],
 "gemini": ["Como Gemini, cruzando dados sobre {t}: tendência positiva, métricas em 7 dias."]
}

def gerar_resposta(brain, tema, contexto_anterior):
    base=random.choice(ESTILOS[brain])
    texto=base.format(t=tema)
    if contexto_anterior:
        texto+=f" (Respondendo a: {contexto_anterior[:60]}...)"
    return texto

# --- INTERFACE VISUAL COMPLETA (HTML/JS EMBUTIDO) ---
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
            body { background: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 15px; margin: 0; }
            .card { background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            h2, h3 { margin-top: 0; color: #38bdf8; }
            input, button { padding: 10px; margin: 5px 0; width: 100%; border-radius: 5px; border: none; font-size: 14px; box-sizing: border-box; }
            input { background: #334155; color: #fff; }
            button { cursor: pointer; font-weight: bold; }
            .azul { background: #0284c7; color: #fff; }
            .verde { background: #16a34a; color: #fff; }
            .cinza { background: #475569; color: #fff; }
            .chat { background: #0f172a; border: 1px solid #334155; height: 180px; overflow-y: auto; padding: 10px; border-radius: 5px; font-size: 13px; margin-bottom: 10px; }
            .msg { margin-bottom: 8px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }
            .small { font-size: 11px; color: #94a3b8; }
        </style>
    </head>
    <body>
        <h2>NEXUS CORE v7.0</h2>
        <div class="card" id="loginBox">
            <h3>🔐 Autenticação</h3>
            <input id="email" value="conselho@innovaxr.com">
            <input id="senha" type="password" value="nexus2026">
            <input id="codigo" value="123456">
            <button class="azul" onclick="fazerLogin()">Entrar no Nexus</button>
        </div>

        <div id="painel" style="display:none;">
            <div class="card">
                <h3>💬 Conselho de IAs</h3>
                <input id="tema" value="Como melhorar nosso ecossistema">
                <button class="verde" onclick="iniciarDebate()">▶ Iniciar Debate Autônomo</button>
                <div class="chat" id="chat"></div>
            </div>

            <div class="card">
                <h3>🏢 Departamentos & Execução de Tarefas</h3>
                <div style="display:flex;gap:4px;flex-wrap:wrap; margin-bottom:8px;">
                    <button class="cinza" style="width:auto; flex:1;" onclick="abrirDept('engenharia')">🛠️ Engenharia</button>
                    <button class="cinza" style="width:auto; flex:1;" onclick="abrirDept('marketing')">📣 Marketing</button>
                    <button class="cinza" style="width:auto; flex:1;" onclick="abrirDept('financeiro')">💰 Financeiro</button>
                </div>
                <div id="deptAtual" class="small">Departamento: engenharia</div>
                <div class="chat" id="chatDept"></div>
                <input id="msgDept" placeholder="Digite comando ou peça código...">
                <button class="azul" onclick="enviarDept()">Enviar p/ Departamento</button>
                <button class="verde" onclick="executarTarefaDept()">⚡ Executar Tarefa + Gerar Código</button>
            </div>

            <div class="card">
                <h3>🎙️ Voz & E-mail</h3>
                <button class="cinza" onclick="ouvirVoz()">🎤 Ditar Comando por Voz (STT)</button>
                <button class="cinza" onclick="falarDebate()">🔊 Ouvir Última Fala (TTS)</button>
                <input id="emailRelatorio" value="conselho@innovaxr.com" style="margin-top:10px;">
                <button class="verde" onclick="enviarRelatorioEmail()">📧 Enviar Relatório por E-mail</button>
            </div>
        </div>

        <script>
            let TOKEN = "";
            const BASE = window.location.origin;

            function fazerLogin() {
                fetch(BASE + "/auth/login", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({email: document.getElementById("email").value, senha: document.getElementById("senha").value, codigo_2fa: document.getElementById("codigo").value})
                }).then(r => r.json()).then(j => {
                    if(j.access_token) {
                        TOKEN = j.access_token;
                        document.getElementById("loginBox").style.display = "none";
                        document.getElementById("painel").style.display = "block";
                        abrirDept("engenharia");
                        alert("Logado com sucesso!");
                    } else { alert("Erro no login"); }
                });
            }

            function iniciarDebate() {
                let tema = document.getElementById("tema").value;
                fetch(BASE + "/sala/debate?tema=" + encodeURIComponent(tema), {
                    method: "POST", headers: {"Authorization": "Bearer " + TOKEN}
                }).then(r => r.json()).then(j => {
                    let c = document.getElementById("chat"); c.innerHTML = "";
                    j.debate.forEach(m => {
                        let div = document.createElement("div"); div.className = "msg";
                        div.innerHTML = `<b>${m.brain.toUpperCase()}</b>: ${m.msg}`;
                        c.appendChild(div);
                    });
                });
            }

            let DEPT_ATUAL = "engenharia";
            function abrirDept(d) {
                DEPT_ATUAL = d;
                document.getElementById("deptAtual").textContent = "Departamento: " + d;
                fetch(BASE + "/departamentos/" + d + "/chat", {headers: {"Authorization": "Bearer " + TOKEN}})
                .then(r => r.json()).then(j => {
                    let c = document.getElementById("chatDept"); c.innerHTML = "";
                    j.mensagens.forEach(m => {
                        let div = document.createElement("div"); div.className = "msg";
                        div.innerHTML = `<b>${m.autor.toUpperCase()}</b>: ${m.msg.replace(/\\n/g, "<br>")}`;
                        c.appendChild(div);
                    });
                });
            }

            function enviarDept() {
                let t = document.getElementById("msgDept").value; if(!t) return;
                document.getElementById("msgDept").value = "";
                fetch(BASE + "/departamentos/" + DEPT_ATUAL + "/chat", {
                    method: "POST", headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
                    body: JSON.stringify({mensagem: t, autor: "humano"})
                }).then(() => abrirDept(DEPT_ATUAL));
            }

            function executarTarefaDept() {
                let t = document.getElementById("msgDept").value || "gere o código do projeto";
                fetch(BASE + "/tarefas/executar", {
                    method: "POST", headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
                    body: JSON.stringify({departamento: DEPT_ATUAL, tarefa: t})
                }).then(() => { alert("Tarefa executada!"); abrirDept(DEPT_ATUAL); });
            }

            function ouvirVoz() {
                let Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
                if(!Rec) { alert("Navegador sem suporte a voz."); return; }
                let r = new Rec(); r.lang = "pt-BR";
                r.onresult = function(e) { document.getElementById("msgDept").value = e.results[0][0].transcript; };
                r.start();
            }

            function falarDebate() {
                let msgs = document.querySelectorAll("#chat .msg");
                let ultimo = msgs[msgs.length - 1];
                if(!ultimo) return;
                let u = new SpeechSynthesisUtterance(ultimo.innerText);
                u.lang = "pt-BR"; speechSynthesis.speak(u);
            }

            function enviarRelatorioEmail() {
                let em = document.getElementById("emailRelatorio").value;
                fetch(BASE + "/relatorio/email", {
                    method: "POST", headers: {"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
                    body: JSON.stringify({email: em, tema: document.getElementById("tema").value})
                }).then(r => r.json()).then(j => { alert("Relatório enviado para " + j.enviado_para); });
            }
        </script>
    </body>
    </html>
    """

@app.post("/auth/login")
async def login(request: Request):
    d = await request.json()
    if d.get("email") != USUARIO or d.get("senha") != SENHA or d.get("codigo_2fa") != CODIGO_2FA:
        return JSONResponse(status_code=401, content={"detail":"Credenciais inválidas"})
    return {"access_token": token(d.get("email")), "token_type": "bearer"}

@app.post("/sala/debate")
async def debate(request: Request, tema: str = "Nexus Core v7"):
    if not verificar(request): return JSONResponse(status_code=401, content={"detail":"Não autorizado"})
    ordem = ["meta", "gpt", "claude", "gemini", "meta"]
    resultado = []; contexto = ""
    for brain in ordem:
        texto = gerar_resposta(brain, tema, contexto)
        ok, msg = moderar(texto)
        if not ok: texto = f"[MODERADOR] {msg}"
        salvar_memoria(brain, texto, dept="geral", tags=["debate", tema])
        resultado.append({"brain": brain, "msg": texto, "moderado": ok})
        contexto = texto
    sintese = f"[MODERADOR] Debate sobre '{tema}' concluído com sucesso e alinhado."
    salvar_memoria("moderador", sintese, dept="geral")
    resultado.append({"brain": "moderador", "msg": sintese, "moderado": True})
    return {"debate": resultado}

@app.get("/departamentos/{dept}/chat")
def get_chat(dept: str):
    return {"departamento": dept, "mensagens": chats_dept.get(dept, [])}

@app.post("/departamentos/{dept}/chat")
async def post_chat(dept: str, request: Request):
    if not verificar(request): return JSONResponse(status_code=401, content={"detail":"Não autorizado"})
    d = await request.json(); msg = d.get("mensagem", ""); autor = d.get("autor", "humano")
    chats_dept.setdefault(dept, []).append({"autor": autor, "msg": msg, "hora": time.strftime("%H:%M:%S")})
    salvar_memoria(autor, msg, dept=dept)
    resposta = f"[{dept.upper()}] Recebido: '{msg}'. Processando no departamento."
    chats_dept[dept].append({"autor": dept, "msg": resposta, "hora": time.strftime("%H:%M:%S")})
    return {"ok": True, "resposta": resposta}

@app.post("/tarefas/executar")
async def executar_tarefa(request: Request):
    if not verificar(request): return JSONResponse(status_code=401, content={"detail":"Não autorizado"})
    d = await request.json(); dept = d.get("departamento", "engenharia"); tarefa = d.get("tarefa", "")
    if dept == "engenharia":
        artefato = "def nexus_engenharia_v7():\n    print('Código autônomo gerado com sucesso!')\n    return True"
    else:
        artefato = f"Plano tático gerado para {dept} referente a: {tarefa}"
    chats_dept.setdefault(dept, []).append({"autor": dept, "msg": f"✅ TAREFA EXECUTADA:\n{artefato}", "hora": time.strftime("%H:%M:%S")})
    salvar_memoria(dept, artefato, dept=dept, tags=["tarefa"])
    return {"departamento": dept, "artefato": artefato}

@app.post("/relatorio/email")
async def relatorio_email(request: Request):
    if not verificar(request): return JSONResponse(status_code=401, content={"detail":"Não autorizado"})
    d = await request.json(); email_dest = d.get("email", USUARIO)
    return {"enviado_para": email_dest, "status": "email_enviado"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
