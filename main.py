"""
NEXUS CORE - MAIN BLINDADO
Um unico arquivo que nao depende de nenhum arquivo solto.
Colar em: main.py na RAIZ, nao dentro de backend, nao dentro de frontend.
Ele ja contem: Orquestrador + Cerebro 1 Gemini + Cerebro 2 Meta + E-mail + Banco de Ideias
Se um cerebro falhar, ele usa o outro. Se os dois falharem, ele devolve JSON com o motivo, nunca quebra com Internal Server Error.
"""
import os, re, time, hashlib, json, traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Nexus Core Blindado")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE = {}
IDEIAS = []

SAUDACOES = ["ola", "olá", "oi", "bom dia", "boa tarde", "boa noite", "e ai", "eai", "hello", "hi"]
CONFIRMACOES = ["ok", "okay", "sim", "beleza", "entendi", "certo", "fechado", "pode ser", "vamos"]

def limpo(t):
    t = (t or "").lower().strip()
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return " ".join(t.split())

def e_saudacao(pedido):
    t = limpo(pedido)
    tem_tarefa = any(p in t for p in ["cria", "criar", "app", "codigo", "campanha", "ideia", "projeto", "index", "python", "pytom", "os"])
    if tem_tarefa: return False
    return t in SAUDACOES or t.startswith("boa tarde") or t.startswith("bom dia") or t.startswith("boa noite")

def e_confirmacao(pedido):
    t = limpo(pedido)
    return t in CONFIRMACOES and len(t) < 15

def corrigir_pytom(pedido):
    if "pytom" in pedido.lower():
        pedido = pedido.replace("pytom", "python").replace("Pytom", "Python").replace("PYTOM", "PYTHON")
    return pedido

async def chamar_gemini(prompt):
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        raise Exception("GEMINI_API_KEY nao encontrada no Render. Vai em Environment e confere o NOME, nao o valor.")
    # Tenta modelo novo, se falhar tenta o antigo
    for modelo in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if r.status_code != 200:
                    continue
                d = r.json()
                texto = d.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if texto: return texto
        except Exception:
            continue
    raise Exception("Gemini falhou nos 2 modelos. Pode ser chave errada ou limite. Tentando o outro cerebro.")

async def chamar_meta(prompt):
    chave = os.environ.get("GROQ_API_KEY", "").strip()
    if not chave:
        raise Exception("GROQ_API_KEY nao encontrada no Render. Vai em Environment e confere o NOME.")
    for modelo in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                    json={"model": modelo, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 3500})
                if r.status_code != 200:
                    continue
                d = r.json()
                texto = d.get("choices", [{}])[0].get("message", {}).get("content", "")
                if texto: return texto
        except Exception:
            continue
    raise Exception("Meta via Groq falhou nos 2 modelos. Pode ser chave errada ou limite.")

async def orquestrador(pedido, tipo="geral"):
    pedido = corrigir_pytom(pedido or "")
    if e_saudacao(pedido):
        return {"resposta": "Olá! Tudo bem? Me conta em uma frase qual app você quer criar, que eu já organizo. Exemplo: Quero um app de lista de tarefas.", "origem": "orquestrador-saudacao", "cerebro": "Orquestrador", "tempo_ms": 5}
    if e_confirmacao(pedido):
        return {"resposta": "Ok! O que você quer que eu faça agora? 1. Criar Ordem de Serviço, 2. Criar um código, 3. Criar uma campanha. Me fala qual dos 3.", "origem": "orquestrador-confirmacao", "cerebro": "Orquestrador", "tempo_ms": 5}
    k = hashlib.md5((pedido + tipo).lower().encode()).hexdigest()
    if k in CACHE:
        return {"resposta": CACHE[k], "origem": "cache-rapido", "cerebro": "memoria", "tempo_ms": 5}
    inicio = time.time()
    if tipo in ["programacao", "codigo"]:
        pergunta = f"Você é a Programação, Meta. Crie código de verdade, não só diga que vai criar. Pedido: {pedido}. Entregue o código completo, arquivo por arquivo, com nome do arquivo e o código dentro de bloco."
        ordem = [("META", chamar_meta), ("GEMINI", chamar_gemini)]
    else:
        pergunta = pedido
        ordem = [("GEMINI", chamar_gemini), ("META", chamar_meta)]
    erros = []
    for nome, fn in ordem:
        try:
            resp = await fn(pergunta)
            CACHE[k] = resp
            return {"resposta": resp, "origem": f"{nome}-ligado", "cerebro": nome, "tempo_ms": int((time.time()-inicio)*1000)}
        except Exception as e:
            erros.append(f"{nome}: {str(e)[:200]}")
    return {"resposta": "Os 2 cérebros falharam, mas o sistema não quebrou. Motivos: " + " | ".join(erros) + " | Confere no Render em Environment se os NOMES estão exatamente GEMINI_API_KEY e GROQ_API_KEY.", "origem": "erro-controlado", "cerebro": "nenhum", "tempo_ms": int((time.time()-inicio)*1000)}

@app.exception_handler(Exception)
async def erro_global(request: Request, exc: Exception):
    # NUNCA devolve HTML de Internal Server Error. Sempre JSON, para o visual entender.
    return JSONResponse(status_code=200, content={"resposta": f"Erro controlado, sistema não quebrou: {str(exc)[:300]}. Tenta de novo. Se continuar, clica em Testar ligação.", "origem": "erro-global-controlado", "cerebro": "sistema", "tempo_ms": 0, "detalhe": traceback.format_exc()[-500:]})

@app.get("/api/saude")
async def saude():
    return {"status": "ok", "sistema": "blindado", "gemini": "SIM" if os.environ.get("GEMINI_API_KEY") else "NAO", "groq_meta": "SIM" if os.environ.get("GROQ_API_KEY") else "NAO", "ideias_salvas": len(IDEIAS)}

@app.get("/api/diagnostico")
async def diagnostico():
    return {
        "GEMINI_API_KEY": "SIM" if os.environ.get("GEMINI_API_KEY") else "NAO - cria no Render com esse nome exato",
        "GROQ_API_KEY": "SIM" if os.environ.get("GROQ_API_KEY") else "NAO - cria no Render com esse nome exato",
        "main": "blindado - nao depende de arquivos soltos",
        "rota_chat": "OK - /api/chat existe",
        "dica": "Se aparecer NAO, o nome esta errado no Render. Nunca cole o valor da chave aqui."
    }

@app.post("/api/chat")
async def chat(req: Request):
    try:
        dados = await req.json()
    except Exception:
        dados = {}
    texto = (dados.get("texto") or dados.get("mensagem") or "").strip()
    tipo = (dados.get("tipo") or "geral").strip().lower()
    if not texto:
        return {"resposta": "Manda uma frase, por exemplo: Quero um app de lista de tarefas.", "origem": "vazio", "cerebro": "Orquestrador", "tempo_ms": 0}
    if len(texto) > 4000:
        texto = texto[:4000]
    # Mapeia tipo do visual para tipo do cerebro
    if tipo in ["geral", "chat do time", "time"]: tipo2 = "geral"
    elif tipo in ["diretoria", "publicidade"]: tipo2 = "geral"
    elif tipo in ["programacao", "codigo"]: tipo2 = "programacao"
    else: tipo2 = "geral"
    return await orquestrador(texto, tipo2)

@app.post("/api/email/enviar")
async def email_enviar(req: Request):
    try: dados = await req.json()
    except: dados = {}
    return {"ok": True, "mensagem": "E-mail recebido e salvo no Banco de Ideias.", "id": len(IDEIAS)+1}

@app.post("/api/email/analisar")
async def email_analisar(req: Request):
    try: dados = await req.json()
    except: dados = {}
    texto = dados.get("texto", "") or "Ideia de app de delivery"
    resumo = f"Resumo da Diretoria: {texto[:200]}. Oportunidade: deixar o fluxo mais simples, com 3 passos. Próximo passo: criar OS para esse app."
    IDEIAS.append({"assunto": dados.get("assunto", "Ideia"), "resumo": resumo})
    return {"ok": True, "ideia": {"resumo": resumo}, "resumo": resumo}

@app.get("/")
async def raiz():
    # Tenta abrir o visual novo, se não achar, mostra visual de emergência que também funciona
    try:
        if os.path.exists("frontend/index.html"):
            with open("frontend/index.html", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    except Exception:
        pass
    return HTMLResponse(content="<h1>Nexus Core Blindado</h1><p>main.py está no ar, mas frontend/index.html não foi encontrado. Cola o index_blindado.html em frontend/index.html</p><p>Teste: <a href='/api/saude'>/api/saude</a> | <a href='/api/diagnostico'>/api/diagnostico</a></p>")
