"""
NEXUS CORE - FINAL PRONTO
Colar em: main.py na RAIZ
- NUNCA tem chave dentro do codigo. So le o NOME da chave no Render.
- Livre arbitrio: qualquer tema responde, nao so app.
- Cria imagem, cria codigo, cria HTML.
- Se as 2 chaves falharem, usa cerebro local e NAO fala "falharam".
- Diagnostico real: testa a chave e fala o motivo exato (400, 403, 429, espaco, etc)
"""
import os, re, time, hashlib, json, traceback, urllib.parse, random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Nexus Core Final")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
CACHE = {}
IDEIAS = []

# ---------- CHAVES: so le o NOME, nunca o valor, e limpa espaco ----------
def pegar_chave(nomes):
    for nome in nomes:
        v = os.environ.get(nome, "")
        if v:
            v = v.strip().strip('"').strip("'").strip()
            v = v.replace("\n","").replace("\r","").replace(" ","")
            if v and len(v) > 10:
                return v, nome
    return None, None

GEMINI_NOMES = ["GEMINI_API_KEY","GOOGLE_API_KEY","GOOGLE_GEMINI_API_KEY","GEMINI_KEY"]
GROQ_NOMES = ["GROQ_API_KEY","GROQ_KEY","META_API_KEY","LLAMA_API_KEY"]

# ---------- LIVRE ARBITRIO: qualquer tema ----------
SAUDACOES = ["ola","olá","oi","bom dia","boa tarde","boa noite","e ai","eai","hello","hi"]
CONFIRMACOES = ["ok","okay","sim","beleza","entendi","certo","fechado"]

def limpo(t):
    t = (t or "").lower().strip()
    t = re.sub(r"[^a-z0-9 ]","",t)
    return " ".join(t.split())

def e_saudacao(p):
    t=limpo(p)
    tem_tarefa = any(x in t for x in ["cria","criar","app","codigo","campanha","ideia","projeto","index","python","pytom","imagem","foto","desenha"])
    if tem_tarefa: return False
    return t in SAUDACOES or t.startswith("boa tarde") or t.startswith("bom dia") or t.startswith("boa noite")

def e_confirmacao(p):
    return limpo(p) in CONFIRMACOES

def corrigir(p):
    p=p.replace("pytom","python").replace("Pytom","Python").replace("PYTOM","PYTHON")
    return p

def quer_imagem(p):
    t=p.lower()
    return any(x in t for x in ["imagem","foto","desenho","desenha","logo","banner","capa","ilustra","cria uma imagem","gera imagem","imagem de","quero uma imagem","faz uma imagem","criar imagem"])

def quer_codigo(p):
    t=p.lower()
    return any(x in t for x in ["codigo","código","html","css","javascript","python","app","site","pagina","landing","cria o","crie o","faz um app","criar app","programa"])

def gerar_url_imagem(prompt):
    # Pollinations: gratis, sem chave, funciona sempre
    prompt_limpo = prompt.replace("cria uma imagem de","").replace("cria imagem de","").replace("quero uma imagem de","").strip() or prompt
    seed = random.randint(1,999999)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_limpo)}?width=1024&height=1024&seed={seed}&nologo=true"
    return url, prompt_limpo

# ---------- CEREBRO LOCAL: reserva, para nunca falhar ----------
def cerebro_local(prompt, tipo):
    p = prompt.strip()
    if quer_imagem(prompt):
        url, desc = gerar_url_imagem(p)
        return f"Pronto! Criei sua imagem de: {desc}.\n\n[IMAGEM]{url}[/IMAGEM]\n\nQuer que eu mude alguma coisa? Pode falar: deixa mais colorido, muda o fundo, faz outro estilo, cria um logo, cria um banner."
    if quer_codigo(prompt):
        # Gera um HTML pronto de exemplo, funcional
        codigo = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>App - {p[:30]}</title>
<style>body{{font-family:Arial;background:#0f1115;color:#fff;padding:20px}}input,button{{padding:12px;border-radius:10px;border:0}}button{{background:#2a6cff;color:#fff;font-weight:700}}ul{{list-style:none;padding:0}}li{{background:#1a1e27;padding:10px;margin:6px 0;border-radius:10px;display:flex;justify-content:space-between}}</style></head>
<body><h1>{p[:50]}</h1><p>App criado pelo Nexus Core. Digite e aperte Adicionar.</p><div><input id="t" placeholder="Digite aqui"><button onclick="add()">Adicionar</button></div><ul id="lista"></ul>
<script>function add(){{var v=document.getElementById('t').value; if(!v) return; var li=document.createElement('li'); li.innerHTML=v+' <span onclick="this.parentElement.remove()" style="cursor:pointer">X</span>'; document.getElementById('lista').appendChild(li); document.getElementById('t').value='';}}</script></body></html>"""
        return f"Pronto! Criei seu código de verdade, completo, pronto para copiar e usar.\n\nPedido: {p}\n\n```html\n{codigo}\n```\n\nComo usar: copia esse código, cola em um arquivo `index.html` e abre no navegador. Quer que eu faça outro? Pode falar: faz versão com login, com banco de dados, com design mais bonito."
    # Livre arbitrio: qualquer tema
    if tipo=="programacao":
        return f"Entendi, você falou sobre: {p}.\n\nComo Programação, vou te ajudar com isso de forma prática.\n\n1. O que isso significa: {p} é um tema que dá para transformar em app, código ou automação.\n2. Como fazer: primeiro a gente define o objetivo, depois eu crio o código arquivo por arquivo.\n3. Exemplo: se você quiser, eu já crio agora um `index.html` completo para isso.\n\nMe fala: quer que eu crie o código agora, ou quer que eu explique mais sobre o tema?"
    if tipo=="publicidade":
        return f"Boa! Você falou sobre: {p}.\n\nComo Publicidade, minha ideia para isso:\n\n- Nome sugerido: {p[:20].title()} Plus\n- Frase: Simples, rápido e feito para você.\n- Campanha: 3 posts: 1. Problema, 2. Solução, 3. Prova. + 1 vídeo curto.\n\nQuer que eu crie também uma imagem para essa campanha? É só falar: cria uma imagem para isso."
    if tipo=="diretoria":
        return f"Entendi, você falou sobre: {p}.\n\nComo Diretoria, vou organizar isso para você.\n\n- Ordem de Serviço: OS para: {p}\n- Objetivo: resolver isso de forma simples e rápida.\n- Passo 1: definir o que você quer no final.\n- Passo 2: Programação cria o código.\n- Passo 3: Publicidade cria nome e campanha.\n\nQuer que eu já transforme isso em OS oficial e chame os outros dois? É só falar: pode criar a OS."
    # Chat do Time - livre arbitrio total
    return f"Entendi, você falou sobre: {p}.\n\nVou te responder com livre arbítrio, como um time de verdade:\n\n- Diretoria: isso é importante porque pode virar um projeto, uma ideia ou um app.\n- Programação: dá para transformar isso em código, em site ou em automação, se você quiser.\n- Publicidade: dá para transformar isso em nome, campanha ou imagem, se você quiser.\n\nMe fala o que você quer agora: quer que eu explique mais sobre esse tema, crie um código, crie uma imagem, ou crie uma Ordem de Serviço? Pode falar de qualquer tema, eu respondo."

# ---------- CHAMADAS REAIS ----------
async def chamar_gemini(prompt):
    chave, nome_usado = pegar_chave(GEMINI_NOMES)
    if not chave:
        raise Exception("SEM_CHAVE: Nenhuma chave Gemini encontrada no Render. Nomes que eu procurei: GEMINI_API_KEY, GOOGLE_API_KEY. Vai em Environment e confere o NOME, sem espaco.")
    for modelo in ["gemini-2.0-flash","gemini-1.5-flash"]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
            async with httpx.AsyncClient(timeout=30) as c:
                r=await c.post(url, json={"contents":[{"parts":[{"text":prompt}]}]})
                if r.status_code==200:
                    d=r.json()
                    txt=d.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
                    if txt: return txt
                elif r.status_code==400:
                    raise Exception("ERRO_400_CHAVE_INVALIDA: O Google disse 400. Sua chave existe, mas esta invalida, expirada ou com espaco. Copia a chave de novo no Google AI Studio, sem espaco no inicio nem no fim, cola no Render e faz Redeploy.")
                elif r.status_code==403:
                    raise Exception("ERRO_403_SEM_PERMISSAO: O Google disse 403. A chave nao tem permissao para usar Gemini. Ativa a API no Google Cloud.")
                elif r.status_code==429:
                    raise Exception("ERRO_429_LIMITE: O Google disse 429. Voce atingiu o limite gratis. Espera 1 minuto e tenta de novo, ou usa o outro cerebro.")
                elif r.status_code==404:
                    continue
                else:
                    continue
        except Exception as e:
            if "ERRO_" in str(e) or "SEM_CHAVE" in str(e): raise
            continue
    raise Exception("ERRO_GEMINI: Gemini nao respondeu nos 2 modelos. Tenta de novo em 30 segundos.")

async def chamar_meta(prompt):
    chave, nome_usado = pegar_chave(GROQ_NOMES)
    if not chave:
        raise Exception("SEM_CHAVE: Nenhuma chave Groq encontrada no Render. Nomes que eu procurei: GROQ_API_KEY, GROQ_KEY. Vai em Environment e confere o NOME.")
    for modelo in ["llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r=await c.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {chave}","Content-Type":"application/json"},
                    json={"model":modelo,"messages":[{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":3500})
                if r.status_code==200:
                    d=r.json()
                    txt=d.get("choices",[{}])[0].get("message",{}).get("content","")
                    if txt: return txt
                elif r.status_code==401:
                    raise Exception("ERRO_401_CHAVE_INVALIDA: O Groq disse 401. Sua chave existe, mas esta invalida ou expirada. Copia de novo no Groq, sem espaco, cola no Render e faz Redeploy.")
                elif r.status_code==429:
                    raise Exception("ERRO_429_LIMITE: O Groq disse 429. Limite atingido. Espera 1 minuto.")
                elif r.status_code==404:
                    continue
                else:
                    continue
        except Exception as e:
            if "ERRO_" in str(e) or "SEM_CHAVE" in str(e): raise
            continue
    raise Exception("ERRO_META: Meta via Groq nao respondeu nos 2 modelos.")

async def orquestrador(pedido, tipo="geral"):
    pedido=corrigir(pedido or "")
    if e_saudacao(pedido):
        return {"resposta":"Olá! Tudo bem? Pode falar de qualquer tema, que eu respondo. Pode ser: criar um app, criar uma imagem, criar um código, uma ideia, uma dúvida, qualquer coisa. O que você quer hoje?","origem":"orquestrador-saudacao","cerebro":"Orquestrador","tempo_ms":5}
    if e_confirmacao(pedido):
        return {"resposta":"Ok! O que você quer que eu faça agora? Pode ser: 1. Criar uma imagem, 2. Criar um código HTML, 3. Criar uma Ordem de Serviço, 4. Falar de qualquer tema. Me fala qual.","origem":"orquestrador-confirmacao","cerebro":"Orquestrador","tempo_ms":5}
    k=hashlib.md5((pedido+tipo).lower().encode()).hexdigest()
    if k in CACHE:
        return {"resposta":CACHE[k],"origem":"cache-rapido","cerebro":"memoria","tempo_ms":5}
    # Imagem: cria direto, sem depender de chave, para nunca falhar
    if quer_imagem(pedido):
        url, desc = gerar_url_imagem(pedido)
        resp = f"Pronto! Criei sua imagem de: {desc}.\n\n[IMAGEM]{url}[/IMAGEM]\n\nQuer que eu mude? Pode falar: mais colorido, outro fundo, estilo desenho, estilo foto real, cria um logo, cria um banner."
        CACHE[k]=resp
        return {"resposta":resp,"origem":"imagem-pollinations-sem-chave","cerebro":"Criador de Imagem","tempo_ms":50}
    inicio=time.time()
    # Persona com livre arbitrio: cada um pode falar de qualquer tema
    if tipo=="programacao":
        pergunta=f"Você é a Programação, comandada pela Meta. Você tem livre arbítrio para falar de qualquer tema. Se o usuário pedir código, crie código de verdade, completo, arquivo por arquivo. Se pedir outro tema, responda sobre esse tema e sugira como transformar em código. Pedido: {pedido}"
        ordem=[("META",chamar_meta),("GEMINI",chamar_gemini)]
    elif tipo=="publicidade":
        pergunta=f"Você é a Publicidade, comandada pelo Gemini. Você tem livre arbítrio para falar de qualquer tema. Se o usuário pedir campanha, crie nome, frase e campanha. Se pedir outro tema, responda sobre esse tema e sugira uma campanha. Pedido: {pedido}"
        ordem=[("GEMINI",chamar_gemini),("META",chamar_meta)]
    elif tipo=="diretoria":
        pergunta=f"Você é a Diretoria, comandada pelo Gemini. Você tem livre arbítrio para falar de qualquer tema. Se o usuário pedir OS, crie OS. Se pedir outro tema, responda sobre esse tema e organize em passos. Pedido: {pedido}"
        ordem=[("GEMINI",chamar_gemini),("META",chamar_meta)]
    else:
        pergunta=f"Você é o Chat do Time, com 3 inteligências: Diretoria, Programação e Publicidade. Vocês têm livre arbítrio para falar de qualquer tema. Respondam sobre: {pedido}. Se for pedido de código, entreguem código completo. Se for pedido de imagem, descrevam a imagem. Se for qualquer outro tema, respondam com profundidade, exemplos e próximos passos."
        ordem=[("GEMINI",chamar_gemini),("META",chamar_meta)]
    erros=[]
    for nome, fn in ordem:
        try:
            resp=await fn(pergunta)
            CACHE[k]=resp
            return {"resposta":resp,"origem":f"{nome}-ligado","cerebro":nome,"tempo_ms":int((time.time()-inicio)*1000)}
        except Exception as e:
            erros.append(str(e)[:250])
    # NUNCA fala "falharam". Usa cerebro local e avisa o motivo real em pequeno, mas entrega resposta util.
    local = cerebro_local(pedido, tipo)
    aviso = f"\n\n---\nAviso técnico (não é erro seu): as 2 chaves não responderam agora. Motivos reais: {' | '.join(erros)} | Mas eu respondi com o cérebro local para você não ficar sem resposta. Para voltar ao Gemini e Meta, confere o diagnóstico em /api/diagnostico."
    resp_final = local + aviso
    CACHE[k]=resp_final
    return {"resposta":resp_final,"origem":"cerebro-local-reserva","cerebro":"Local + Aviso","tempo_ms":int((time.time()-inicio)*1000)}

@app.exception_handler(Exception)
async def erro_global(request: Request, exc: Exception):
    return JSONResponse(status_code=200, content={"resposta":f"Erro controlado, não quebrou: {str(exc)[:300]}. Tenta de novo.","origem":"erro-global-controlado","cerebro":"sistema","tempo_ms":0})

@app.get("/api/saude")
async def saude():
    g,_ = pegar_chave(GEMINI_NOMES)
    gr,_ = pegar_chave(GROQ_NOMES)
    return {"status":"ok","sistema":"final-pronto","gemini":"SIM" if g else "NAO","groq_meta":"SIM" if gr else "NAO","ideias_salvas":len(IDEIAS),"livre_arbitrio":"LIGADO","criar_imagem":"LIGADO","criar_codigo":"LIGADO"}

@app.get("/api/diagnostico")
async def diagnostico():
    g, nome_g = pegar_chave(GEMINI_NOMES)
    gr, nome_gr = pegar_chave(GROQ_NOMES)
    # Testa de verdade com ping pequeno
    teste_g = "NAO TESTADO"
    teste_gr = "NAO TESTADO"
    try:
        if g:
            async with httpx.AsyncClient(timeout=10) as c:
                r=await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={g}", json={"contents":[{"parts":[{"text":"Ola"}]}]})
                if r.status_code==200: teste_g="OK - chave funcionando"
                elif r.status_code==400: teste_g="ERRO 400 - chave invalida, expirada ou com espaco. Copia de novo sem espaco."
                elif r.status_code==403: teste_g="ERRO 403 - sem permissao"
                elif r.status_code==429: teste_g="ERRO 429 - limite, espera 1 minuto"
                else: teste_g=f"ERRO {r.status_code} - {r.text[:150]}"
        else:
            teste_g="SEM CHAVE - cria no Render com nome GEMINI_API_KEY"
    except Exception as e:
        teste_g=f"ERRO: {str(e)[:150]}"
    try:
        if gr:
            async with httpx.AsyncClient(timeout=10) as c:
                r=await c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {gr}","Content-Type":"application/json"}, json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"Ola"}],"max_tokens":10})
                if r.status_code==200: teste_gr="OK - chave funcionando"
                elif r.status_code==401: teste_gr="ERRO 401 - chave invalida ou expirada. Copia de novo sem espaco."
                elif r.status_code==429: teste_gr="ERRO 429 - limite, espera 1 minuto"
                else: teste_gr=f"ERRO {r.status_code} - {r.text[:150]}"
        else:
            teste_gr="SEM CHAVE - cria no Render com nome GROQ_API_KEY"
    except Exception as e:
        teste_gr=f"ERRO: {str(e)[:150]}"
    return {"GEMINI_API_KEY": "SIM" if g else "NAO", "nome_encontrado_gemini": nome_g or "nenhum", "teste_gemini": teste_g, "GROQ_API_KEY": "SIM" if gr else "NAO", "nome_encontrado_groq": nome_gr or "nenhum", "teste_groq": teste_gr, "aviso": "Se aparecer SIM mas teste 400/401, a chave existe mas esta com espaco ou expirada. Copia de novo, sem espaco, cola no Render e faz Redeploy. O codigo nunca tem a chave dentro."}

@app.post("/api/chat")
async def chat(req: Request):
    try: dados=await req.json()
    except: dados={}
    texto=(dados.get("texto") or dados.get("mensagem") or "").strip()
    tipo=(dados.get("tipo") or "geral").strip().lower()
    if not texto:
        return {"resposta":"Manda uma frase, de qualquer tema. Pode ser: cria uma imagem de um gato, cria um app, o que é buraco negro, me dá uma ideia.","origem":"vazio","cerebro":"Orquestrador","tempo_ms":0}
    if len(texto)>4000: texto=texto[:4000]
    if tipo in ["geral","chat do time","time"]: tipo2="geral"
    elif tipo in ["diretoria"]: tipo2="diretoria"
    elif tipo in ["programacao","codigo"]: tipo2="programacao"
    elif tipo in ["publicidade"]: tipo2="publicidade"
    else: tipo2="geral"
    return await orquestrador(texto, tipo2)

@app.post("/api/imagem")
async def imagem(req: Request):
    try: dados=await req.json()
    except: dados={}
    prompt=dados.get("prompt") or dados.get("texto") or "imagem bonita"
    url, desc = gerar_url_imagem(prompt)
    return {"ok":True,"url":url,"descricao":desc}

@app.post("/api/email/enviar")
async def email_enviar(req: Request):
    try: dados=await req.json()
    except: dados={}
    IDEIAS.append(dados)
    return {"ok":True,"mensagem":"E-mail recebido e salvo.","id":len(IDEIAS)}

@app.post("/api/email/analisar")
async def email_analisar(req: Request):
    try: dados=await req.json()
    except: dados={}
    texto=dados.get("texto","") or "Ideia de app"
    resumo=f"Resumo da Diretoria: {texto[:200]}. Oportunidade: deixar mais simples, com 3 passos. Proximo: criar OS."
    IDEIAS.append({"assunto":dados.get("assunto","Ideia"),"resumo":resumo})
    return {"ok":True,"ideia":{"resumo":resumo},"resumo":resumo}

@app.get("/")
async def raiz():
    try:
        if os.path.exists("frontend/index.html"):
            with open("frontend/index.html", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    except Exception:
        pass
    return HTMLResponse(content="<h1>Nexus Core Final</h1><p>main.py no ar. Cola o index_final.html em frontend/index.html</p><p><a href='/api/saude'>/api/saude</a> | <a href='/api/diagnostico'>/api/diagnostico</a></p>")
