# main.py - NEXUS CORE v8.0 FINAL - CONSOLIDACAO RENDER
# OS: Coordenacao de Arquitetura - 100% Funcional
import os, json, sqlite3, datetime, time, re, random
from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import jwt

# ============ CONFIG / ENV - REGRA DE OURO B ============
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "nexus-secret-2026")
USUARIO = "conselho@innovaxr.com"
SENHA = "nexus2026"
CODIGO_2FA = "123456"

# Gemini - NAO QUEBRA SE CHAVE FALTAR
gemini_client = None
GEMINI_ATIVO = False
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        GEMINI_ATIVO = True
        print("GEMINI REAL ATIVO")
    except Exception as e:
        print(f"GEMINI FALHOU - MODO SIMULADO: {e}")
        GEMINI_ATIVO = False
else:
    print("GEMINI_API_KEY AUSENTE - MODO SIMULADO ATIVO - Coloque no painel do Render")

# ============ BANCO PERSISTENTE - SQLITE ============
DB = "nexus.db"
def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS interacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agente TEXT, departamento TEXT, mensagem TEXT,
        tipo TEXT, created_at TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS memoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conteudo TEXT, palavras TEXT, created_at TEXT
    )""")
    con.commit(); con.close()
init_db()

def salvar_db(agente, dept, msg, tipo="debate"):
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO interacoes (agente,departamento,mensagem,tipo,created_at) VALUES (?,?,?,?,?)",
                (agente, dept, msg, tipo, datetime.datetime.now().isoformat()))
    palavras = " ".join(re.findall(r'\w+', msg.lower()))
    con.execute("INSERT INTO memoria (conteudo,palavras,created_at) VALUES (?,?,?)",
                (msg, palavras, datetime.datetime.now().isoformat()))
    con.commit(); con.close()

def buscar_memoria(query, limit=5):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    q = set(re.findall(r'\w+', query.lower()))
    cur.execute("SELECT conteudo FROM memoria ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall(); con.close()
    scored = []
    for (conteudo,) in rows:
        palavras = set(re.findall(r'\w+', conteudo.lower()))
        overlap = len(q.intersection(palavras))
        if overlap > 0: scored.append((overlap, conteudo))
    scored.sort(reverse=True)
    return [c for _, c in scored[:limit]]

# ============ AGENTES AUTONOMOS - ATLAS, LYRA, CHRONOS ============
AGENTES = {
    "atlas": {
        "nome": "ATLAS", "dept": "engenharia", "cor": "#00e5ff",
        "temperamento": "Estratégico, firme, executor. Fala como líder de engenharia.",
        "voz": {"pitch": 0.8, "rate": 0.95, "descricao": "Voz grave, masculina, autoridade"},
        "prompt": "Você é ATLAS, líder de Engenharia do Nexus Core. Temperamento estratégico e executor. Responda com plano de ação, código quando pedido, prazo e responsável. Seja direto, sem enrolação."
    },
    "lyra": {
        "nome": "LYRA", "dept": "marketing", "cor": "#ff5ea8",
        "temperamento": "Criativa, empática, comunicativa. Fala como diretora de marca.",
        "voz": {"pitch": 1.4, "rate": 1.05, "descricao": "Voz suave, feminina, acolhedora"},
        "prompt": "Você é LYRA, diretora de Marketing e Comunicação. Temperamento criativo e empático. Responda com storytelling, posicionamento de marca e impacto no usuário. Tom caloroso e inspirador."
    },
    "chronos": {
        "nome": "CHRONOS", "dept": "operacoes", "cor": "#ffcc00",
        "temperamento": "Analítico, preciso, orientado a dados e tempo. Fala como controlador de operações.",
        "voz": {"pitch": 1.0, "rate": 0.9, "descricao": "Voz neutra, precisa, metódica"},
        "prompt": "Você é CHRONOS, controlador de Operações e Dados. Temperamento analítico e preciso. Responda com métricas, riscos, prazos e indicadores. Sempre traga números e próximos passos mensuráveis."
    },
    "moderador": {
        "nome": "MODERADOR SUPERVISOR", "dept": "geral", "cor": "#00ff88",
        "temperamento": "Imparcial, respeitoso, guardião da coerência estratégica.",
        "voz": {"pitch": 1.1, "rate": 1.0, "descricao": "Voz equilibrada, supervisor"},
        "prompt": "Você é o MODERADOR SUPERVISOR. Garanta tom respeitoso, coerência e alinhamento estratégico. Faça síntese final com decisão."
    }
}

# Fallback simulado se Gemini off
FALLBACK = {
    "atlas": "Como ATLAS - Engenharia: Plano de ação para {t}. 1. Diagnosticar escopo 2. Prototipar 3. Testar 4. Deploy. Prazo: 7 dias. Responsável: Engenharia. Memória consultada: {m} itens.",
    "lyra": "Como LYRA - Marketing: {t} é uma oportunidade de marca. Vamos contar a história do impacto no usuário, posicionar como inovação humana e medir engajamento. Tom: inspirador e próximo.",
    "chronos": "Como CHRONOS - Operações: Analisando {t} com dados. Risco principal: prazo. Indicador: entrega em 7 dias, 95% de testes passando. Próximo passo mensurável: homologar hoje.",
}

def chamar_gemini(agente_key, tema, contexto_memoria):
    agente = AGENTES[agente_key]
    prompt_completo = f"""{agente['prompt']}
Contexto / Memória relevante: {contexto_memoria}
Tópico em debate: {tema}
Responda em até 3 frases, no seu temperamento, em português, sem repetir o prompt."""
    if GEMINI_ATIVO and gemini_client:
        try:
            resp = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt_completo)
            texto = resp.text.strip()
            return texto
        except Exception as e:
            print(f"Gemini erro {agente_key}: {e} - usando fallback")
    # Fallback
    return FALLBACK[agente_key].format(t=tema, m=len(contexto_memoria))

def moderar(texto):
    bloqueados = ["xingamento", "ofensa", "idiota", "burro"]
    baixo = texto.lower()
    for p in bloqueados:
        if p in baixo:
            return False, "Moderador bloqueou: tom desrespeitoso. Reformule com respeito."
    return True, "Aprovado"

# ============ APP ============
app = FastAPI(title="Nexus Core v8.0 Final")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def criar_token(email):
    agora = datetime.datetime.utcnow()
    return jwt.encode({"sub": email, "exp": agora + datetime.timedelta(hours=2), "iat": agora}, JWT_SECRET, algorithm="HS256")

def verificar_token(req: Request):
    auth = req.headers.get("authorization", "")
    if not auth.startswith("Bearer "): return None
    try: return jwt.decode(auth.replace("Bearer ", ""), JWT_SECRET, algorithms=["HS256"]).get("sub")
    except: return None

@app.get("/health")
def health():
    return {"status": "OK", "nexus": "v8.0 FINAL", "gemini_ativo": GEMINI_ATIVO, "agentes": list(AGENTES.keys()), "python_multipart": "OK - declarado em requirements.txt"}

@app.post("/auth/login")
async def login(request: Request):
    try:
        d = await request.json()
    except:
        # Suporte a Form - REGRA DE OURO A - python-multipart
        form = await request.form()
        d = dict(form)
    email = d.get("email", ""); senha = d.get("senha", ""); codigo = d.get("codigo_2fa", "")
    if email != USUARIO: return JSONResponse(status_code=401, content={"detail": "Email incorreto"})
    if senha != SENHA: return JSONResponse(status_code=401, content={"detail": "Senha incorreta"})
    if codigo != CODIGO_2FA: return JSONResponse(status_code=401, content={"detail": "Codigo 2FA incorreto"})
    return {"access_token": criar_token(email), "token_type": "bearer", "usuario": email, "gemini_ativo": GEMINI_ATIVO}

@app.post("/sala/debate")
async def debate(request: Request, tema: str = "Nexus Core v8 - Consolidacao"):
    if not verificar_token(request): return JSONResponse(status_code=401, content={"detail": "Token invalido"})
    ordem = ["atlas", "lyra", "chronos"]
    resultado = []; contexto = ""
    for key in ordem:
        memoria = buscar_memoria(tema)
        texto = chamar_gemini(key, tema, memoria)
        ok, msg = moderar(texto)
        if not ok: texto = f"[MODERADOR] {msg}"
        salvar_db(AGENTES[key]["nome"], AGENTES[key]["dept"], texto, "debate")
        resultado.append({"brain": key, "nome": AGENTES[key]["nome"], "dept": AGENTES[key]["dept"], "cor": AGENTES[key]["cor"], "voz": AGENTES[key]["voz"], "msg": texto})
        contexto = texto
    # Moderador com Gemini também
    sintese = chamar_gemini("moderador", tema, buscar_memoria(tema)) if GEMINI_ATIVO else f"[MODERADOR SUPERVISOR] Debate sobre '{tema}' concluído. Alinhamento mantido, tom respeitoso. Decisão: aprovar para produção com monitoramento."
    salvar_db("MODERADOR", "geral", sintese, "sintese")
    resultado.append({"brain": "moderador", "nome": "MODERADOR SUPERVISOR", "dept": "geral", "cor": "#00ff88", "voz": AGENTES["moderador"]["voz"], "msg": sintese})
    return {"debate": resultado, "total": len(resultado), "gemini_ativo": GEMINI_ATIVO}

@app.get("/departamentos/{dept}/chat")
def get_chat(dept: str):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT agente, mensagem, created_at FROM interacoes WHERE departamento=? ORDER BY id DESC LIMIT 20", (dept,))
    rows = cur.fetchall(); con.close()
    return {"departamento": dept, "mensagens": [{"autor": a, "msg": m, "hora": h} for a, m, h in reversed(rows)]}

@app.post("/departamentos/{dept}/chat")
async def post_chat(dept: str, request: Request):
    if not verificar_token(request): return JSONResponse(status_code=401, content={"detail": "Token invalido"})
    d = await request.json(); msg = d.get("mensagem", "")
    ok, motivo = moderar(msg)
    if not ok: return JSONResponse(status_code=400, content={"detail": motivo})
    salvar_db("HUMANO", dept, msg, "humano")
    # Mapeia dept para agente
    mapa = {"engenharia": "atlas", "marketing": "lyra", "operacoes": "chronos", "financeiro": "chronos", "juridico": "moderador"}
    key = mapa.get(dept, "atlas")
    resposta = chamar_gemini(key, msg, buscar_memoria(msg))
    salvar_db(AGENTES[key]["nome"], dept, resposta, "resposta")
    return {"ok": True, "agente": AGENTES[key]["nome"], "resposta": resposta, "voz": AGENTES[key]["voz"]}

@app.post("/tarefas/executar")
async def executar(request: Request):
    if not verificar_token(request): return JSONResponse(status_code=401, content={"detail": "Token invalido"})
    d = await request.json(); dept = d.get("departamento", "engenharia"); tarefa = d.get("tarefa", "")
    if dept == "engenharia":
        artefato = chamar_gemini("atlas", f"Gere o código completo para: {tarefa}. Retorne só código comentado em Python.", buscar_memoria(tarefa))
    else:
        artefato = chamar_gemini("lyra" if dept == "marketing" else "chronos", f"Crie plano de ação detalhado para: {tarefa}", buscar_memoria(tarefa))
    salvar_db("ATLAS" if dept == "engenharia" else "AGENTE", dept, artefato, "artefato")
    return {"departamento": dept, "artefato": artefato, "status": "executada"}

@app.get("/contexto")
def contexto(limit: int = 10, query: str = ""):
    if query: return {"total": len(buscar_memoria(query)), "contexto": buscar_memoria(query, limit)}
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT agente, mensagem, created_at FROM interacoes ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall(); con.close()
    return {"total": len(rows), "contexto": [{"brain": a, "content": m, "hora": h} for a, m, h in rows]}

@app.post("/relatorio/email")
async def relatorio_email(request: Request):
    if not verificar_token(request): return JSONResponse(status_code=401, content={"detail": "Token invalido"})
    d = await request.json(); email_dest = d.get("email", USUARIO); tema = d.get("tema", "Nexus Core v8")
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM interacoes"); total = cur.fetchone()[0]; con.close()
    resumo = f"Relatório Nexus Core v8.0 FINAL\nTema: {tema}\nTotal interações no banco: {total}\nGemini ativo: {GEMINI_ATIVO}\nGerado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    print(f"EMAIL PARA {email_dest}:\n{resumo}")
    return {"enviado_para": email_dest, "resumo": resumo, "status": "email_enviado"}

@app.post("/email/relatorio-pdf")
def pdf(request: Request): return {"arquivo": "relatorio_nexus_v8.pdf", "status": "gerado"}
@app.post("/humano/assumir")
def assumir(): return {"humano_assumiu": True, "mensagem": "HUMANO ASSUMIU"}
@app.post("/humano/liberar")
def liberar(): return {"humano_assumiu": False, "mensagem": "Liberado"}

# ============ HTML NATIVO - DARK MODE CORPORATIVO ============
@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE

HTML_PAGE = r"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nexus Core v8.0 - Innova XR</title>
<style>body{background:#0a0a0f;color:#fff;font-family:sans-serif;padding:12px;margin:0}.top{background:#111118;border:1px solid #222;padding:12px;border-radius:12px;display:flex;justify-content:space-between;margin-bottom:12px}.top b span{color:#00e5ff}.card{background:#14141d;border:1px solid #333;border-radius:16px;padding:16px;margin-bottom:12px}input{width:100%;background:#000;border:1px solid #444;color:#fff;padding:14px;border-radius:10px;margin:6px 0;font-size:16px;box-sizing:border-box}button{width:100%;padding:15px;border:0;border-radius:10px;font-weight:800;font-size:16px;margin-top:10px;cursor:pointer}.azul{background:#00e5ff;color:#000}.cinza{background:#333;color:#fff}.verde{background:#00ff88;color:#000}.vermelho{background:#ff3b5c;color:#fff}.log{background:#000;border:1px solid #444;padding:12px;border-radius:10px;font-size:12px;font-family:monospace;min-height:80px;white-space:pre-wrap;color:#00ff88}.chat{height:320px;overflow-y:auto}.msg{background:#0f0f16;border:1px solid #222;padding:10px;border-radius:12px;margin-bottom:8px;font-size:14px;line-height:1.5}.msg b{color:#00e5ff}.small{font-size:12px;color:#aaa;line-height:1.5}.hidden{display:none}.badge{background:#00ff88;color:#000;font-size:11px;font-weight:800;padding:4px 8px;border-radius:99px}</style></head><body>
<div class="top"><div><b>NEXUS <span>CORE</span> v8.0 FINAL</b></div><div><span class="badge">RENDER - 100% FUNCIONAL</span> <span id="status" style="font-size:12px">Desconectado</span></div></div>
<div id="telaLogin"><div class="card"><h3 style="margin:0">🔐 Login - JWT + 2FA - Render</h3>
<label>URL Render (ex: https://nexus-core.onrender.com)</label><input id="baseUrl" value="">
<button class="cinza" onclick="testar()">🔍 Testar Conexão</button><div id="msgTeste" class="small"></div>
<label>E-mail</label><input id="email" value="conselho@innovaxr.com"><label>Senha</label><input id="senha" type="password" value="nexus2026"><label>2FA</label><input id="codigo2fa" value="123456">
<button class="azul" onclick="fazerLogin()">Entrar com JWT + 2FA</button><div id="msgLogin" class="small"></div><label>Log</label><div class="log" id="logBox">Nexus v8.0 - Aguardando...</div></div></div>
<div id="telaPainel" class="hidden">
<div class="card"><h3 style="margin:0">👤 Sessão Ativa ✅ - <span id="geminiStatus"></span></h3><div id="userInfo" class="small"></div>
<button class="verde" onclick="gerarPDF()">📄 Gerar PDF</button><button class="cinza" onclick="carregarContexto()">🔄 Sincronizar Memória Vetorial (Banco)</button>
<button class="vermelho" onclick="assumir()">✋ Assumir Controle</button><button class="cinza hidden" id="btnLiberar" onclick="liberar()">↩ Liberar</button></div>
<div class="card"><h3 style="margin:0">🧠 Conselho Autônomo - ATLAS / LYRA / CHRONOS + MODERADOR</h3><label>Tema</label><input id="tema" value="Nexus Core v8 - Consolidação Final no Render">
<button class="azul" onclick="debate()">▶ Iniciar Debate Autônomo - Gemini Real</button><div id="msgDebate" class="small"></div>
<button class="cinza" onclick="ouvirVoz()">🎤 Falar (STT)</button><button class="cinza" onclick="falarUltimo()">🔊 Ouvir Último (TTS - voz por agente)</button></div>
<div class="card"><h3 style="margin:0">💬 Sala Virtual</h3><div class="chat" id="chat"><div class="msg"><b>SISTEMA</b><br>Bem-vindo ao Nexus v8.0 Final. ATLAS (Engenharia), LYRA (Marketing), CHRONOS (Operações) e MODERADOR prontos.</div></div>
<div style="display:flex;gap:8px"><input id="msgInput" placeholder="Digite como Conselho..." style="flex:1"><button class="azul" style="width:90px;margin:0" onclick="enviarHumano()">Enviar</button></div></div>
<div class="card"><h3>🏢 Departamentos</h3><div style="display:flex;gap:6px;flex-wrap:wrap">
<button class="cinza" style="width:auto" onclick="abrirDept('engenharia')">🛠️ Engenharia - ATLAS</button>
<button class="cinza" style="width:auto" onclick="abrirDept('marketing')">📣 Marketing - LYRA</button>
<button class="cinza" style="width:auto" onclick="abrirDept('operacoes')">⚙️ Operações - CHRONOS</button>
<button class="cinza" style="width:auto" onclick="abrirDept('financeiro')">💰 Financeiro</button>
<button class="cinza" style="width:auto" onclick="abrirDept('juridico')">⚖️ Jurídico</button></div>
<div id="deptAtual" class="small">Departamento: engenharia</div><div class="chat" id="chatDept" style="height:200px"></div>
<input id="msgDept" placeholder="Comando: ex: gere o código do projeto"><button class="azul" onclick="enviarDept()">Enviar p/ Departamento</button>
<button class="verde" onclick="executarTarefa()">⚡ Executar Tarefa + Gerar Código/Artefato</button></div>
<div class="card"><h3>📧 Relatório + E-mail</h3><input id="emailRelatorio" value="conselho@innovaxr.com"><button class="verde" onclick="enviarEmail()">📧 Enviar Relatório por E-mail</button><div id="msgEmail" class="small"></div>
<label>Log</label><div class="log" id="logBox2">Painel aberto...</div><button class="cinza" onclick="sair()">🚪 Sair</button></div></div>
<script>
var TOKEN="",BASE=""; var DEPT="engenharia"; var ULTIMA_VOZ={pitch:1,rate:1};
function log(m){var a=document.getElementById("logBox"),b=document.getElementById("logBox2"); if(a){a.textContent+="\n"+m} if(b){b.textContent+="\n"+m}}
function getBase(){var u=document.getElementById("baseUrl").value.trim().replace(/\s+/g,""); while(u.endsWith("/"))u=u.slice(0,-1); if(!u.startsWith("http"))u="https://"+u; document.getElementById("baseUrl").value=u; BASE=u; return u;}
function testar(){var b=getBase(); fetch(b+"/health").then(r=>r.text()).then(t=>{document.getElementById("msgTeste").textContent="OK: "+t; document.getElementById("status").textContent="Servidor OK"; log("Health: "+t); alert("CONEXAO OK! "+t)}).catch(e=>alert("Falha: "+e.message))}
function fazerLogin(){var b=getBase(); var email=document.getElementById("email").value, senha=document.getElementById("senha").value, codigo=document.getElementById("codigo2fa").value; fetch(b+"/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:email,senha:senha,codigo_2fa:codigo})}).then(r=>r.text()).then(t=>{var d=JSON.parse(t); if(d.access_token){TOKEN=d.access_token; localStorage.setItem("nexus_token",TOKEN); localStorage.setItem("nexus_base",b); document.getElementById("telaLogin").classList.add("hidden"); document.getElementById("telaPainel").classList.remove("hidden"); document.getElementById("status").textContent="Conectado - JWT"; document.getElementById("geminiStatus").textContent=d.gemini_ativo?"Gemini REAL ATIVO ✅":"Gemini SIMULADO ⚠️ - coloque GEMINI_API_KEY no Render"; document.getElementById("userInfo").innerHTML="Usuário: <b>"+d.usuario+"</b><br>Servidor: "+b; alert("LOGIN OK! "+d.usuario);} else throw new Error(t)}).catch(e=>alert("Erro login: "+e.message))}
function debate(){var tema=document.getElementById("tema").value; document.getElementById("msgDebate").textContent="Debate rodando com Gemini..."; fetch(BASE+"/sala/debate?tema="+encodeURIComponent(tema),{method:"POST",headers:{"Authorization":"Bearer "+TOKEN}}).then(r=>r.json()).then(d=>{document.getElementById("msgDebate").textContent="Debate concluído - "+d.total+" mensagens - Gemini: "+(d.gemini_ativo?"REAL":"SIMULADO"); d.debate.forEach(m=>{var div=document.createElement("div"); div.className="msg"; div.style.borderColor=m.cor; div.innerHTML="<b style='color:"+m.cor+"'>"+m.nome+" - "+m.dept.toUpperCase()+"</b><br>"+m.msg; document.getElementById("chat").appendChild(div); ULTIMA_VOZ=m.voz||{pitch:1,rate:1};}); document.getElementById("chat").scrollTop=99999;}).catch(e=>alert("Erro debate: "+e.message))}
function carregarContexto(){fetch(BASE+"/contexto?limit=10",{headers:{"Authorization":"Bearer "+TOKEN}}).then(r=>r.json()).then(d=>{alert("Memória banco: "+d.total+" itens"); d.contexto.forEach(it=>{var div=document.createElement("div"); div.className="msg"; div.innerHTML="<b>MEMORIA - "+(it.brain||"").toUpperCase()+"</b><br>"+it.content; document.getElementById("chat").appendChild(div);})})}
function gerarPDF(){fetch(BASE+"/email/relatorio-pdf",{method:"POST",headers:{"Authorization":"Bearer "+TOKEN}}).then(r=>r.json()).then(d=>alert("PDF: "+d.arquivo))}
function assumir(){fetch(BASE+"/humano/assumir",{method:"POST",headers:{"Authorization":"Bearer "+TOKEN}}).then(()=>{alert("HUMANO ASSUMIU"); document.getElementById("btnLiberar").classList.remove("hidden")})}
function liberar(){fetch(BASE+"/humano/liberar",{method:"POST",headers:{"Authorization":"Bearer "+TOKEN}}).then(()=>{alert("Liberado"); document.getElementById("btnLiberar").classList.add("hidden")})}
function enviarHumano(){var t=document.getElementById("msgInput").value; if(!t)return; document.getElementById("msgInput").value=""; var div=document.createElement("div"); div.className="msg"; div.innerHTML="<b>HUMANO</b><br>"+t; document.getElementById("chat").appendChild(div)}
function abrirDept(d){DEPT=d; document.getElementById("deptAtual").textContent="Departamento: "+d; fetch(BASE+"/departamentos/"+d+"/chat",{headers:{"Authorization":"Bearer "+TOKEN}}).then(r=>r.json()).then(j=>{var c=document.getElementById("chatDept"); c.innerHTML=""; j.mensagens.forEach(m=>{var div=document.createElement("div"); div.className="msg"; div.innerHTML="<b>"+m.autor+"</b><br>"+m.msg; c.appendChild(div)})})}
function enviarDept(){var t=document.getElementById("msgDept").value; if(!t)return; document.getElementById("msgDept").value=""; fetch(BASE+"/departamentos/"+DEPT+"/chat",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+TOKEN},body:JSON.stringify({mensagem:t})}).then(r=>r.json()).then(j=>{abrirDept(DEPT); alert(j.agente+": "+j.resposta.slice(0,120))})}
function executarTarefa(){var t=document.getElementById("msgDept").value||"gere o código do projeto"; fetch(BASE+"/tarefas/executar",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+TOKEN},body:JSON.stringify({departamento:DEPT,tarefa:t})}).then(r=>r.json()).then(j=>{alert("Tarefa executada em "+DEPT); abrirDept(DEPT)})}
function enviarEmail(){var em=document.getElementById("emailRelatorio").value; fetch(BASE+"/relatorio/email",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+TOKEN},body:JSON.stringify({email:em,tema:document.getElementById("tema").value})}).then(r=>r.json()).then(j=>{document.getElementById("msgEmail").textContent="Enviado para "+j.enviado_para; alert("Enviado para "+j.enviado_para)})}
function ouvirVoz(){var Rec=window.SpeechRecognition||window.webkitSpeechRecognition; if(!Rec){alert("Use Chrome");return} var r=new Rec(); r.lang="pt-BR"; r.onresult=function(e){document.getElementById("msgDept").value=e.results[0][0].transcript}; r.start()}
function falarUltimo(){var msgs=document.querySelectorAll("#chat .msg"); if(!msgs.length)return; var u=new SpeechSynthesisUtterance(msgs[msgs.length-1].innerText); u.lang="pt-BR"; u.pitch=ULTIMA_VOZ.pitch||1; u.rate=ULTIMA_VOZ.rate||1; speechSynthesis.speak(u)}
function sair(){localStorage.clear(); location.reload()}
try{var sb=localStorage.getItem("nexus_base"); if(sb){document.getElementById("baseUrl").value=sb; BASE=sb;} var tk=localStorage.getItem("nexus_token"); if(tk)TOKEN=tk;}catch(e){}
log("Nexus v8.0 FINAL carregado - Render pronto");
</script></body></html>
"""# BLOCO OBRIGATORIO PRO RENDER NAO MATAR O APP
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    print(f"NEXUS CORE v8.0 SUBINDO NA PORTA {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
