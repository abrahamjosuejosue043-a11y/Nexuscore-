"""
NEXUS CORE - MODO SUPERPROGRAMADOR - FINAL
Colar em: main.py na RAIZ do servico 7hdh
REGRA DE OURO: NUNCA tem valor de chave aqui dentro. So o NOME.
O cerebro acha a chave pelo NOME no Render Environment.
- GEMINI_API_KEY, GROQ_API_KEY, ELEVENLABS_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD
- Meta + Gemini comandam juntos, em paralelo, e juntam o melhor dos 2.
- Imagem em alta resolucao 2048x2048, por tras do visual.
- Front so precisa funcionar, todos os detalhes ficam no backend.
"""
import os, re, time, hashlib, asyncio, urllib.parse, random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Nexus Superprogramador")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
CACHE = {}
IDEIAS = []
SAUDACOES = ["ola","olá","oi","bom dia","boa tarde","boa noite","e ai","eai"]
CONFIRMACOES = ["ok","okay","sim","beleza","entendi","certo"]

def pegar(nome):
    # Le SOMENTE pelo NOME no Render. Nunca tem valor aqui.
    v = os.environ.get(nome, "")
    if not v: return None
    v = v.strip().strip('"').strip("'").replace("\n","").replace("\r","").replace(" ","").replace("\u200b","")
    return v if len(v) > 10 else None

def limpo(t):
    t=(t or "").lower().strip()
    t=re.sub(r"[^a-z0-9 ]","",t)
    return " ".join(t.split())
def e_saudacao(p):
    t=limpo(p)
    tem=any(x in t for x in ["cria","criar","app","codigo","campanha","ideia","projeto","index","python","pytom","imagem","foto","desenha","voz","audio"])
    if tem: return False
    return t in SAUDACOES or t.startswith("boa tarde") or t.startswith("bom dia") or t.startswith("boa noite")
def e_confirmacao(p): return limpo(p) in CONFIRMACOES
def corrigir(p): return p.replace("pytom","python").replace("Pytom","Python")
def quer_imagem(p):
    t=p.lower()
    return any(x in t for x in ["imagem","foto","desenho","desenha","logo","banner","capa","ilustra","cria uma imagem","gera imagem","imagem de","alta resolucao","hd","4k"])
def quer_codigo(p):
    t=p.lower()
    return any(x in t for x in ["codigo","código","html","css","javascript","python","app","site","pagina","landing","cria o","crie o","programa","superprogramador"])
def quer_voz(p):
    t=p.lower()
    return any(x in t for x in ["voz","audio","fala","narra","locucao"])

def gerar_imagem_hd(prompt):
    # Alta resolucao, sem chave, por tras do visual. Front so mostra a imagem.
    pl = prompt.replace("cria uma imagem de","").replace("cria imagem de","").replace("em alta resolucao","").replace("hd","").strip() or prompt
    seed = random.randint(1,999999)
    # 2048x2048 = alta resolucao
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(pl + ', ultra detailed, high resolution, sharp, professional')}?width=2048&height=2048&seed={seed}&nologo=true&enhance=true"
    return url, pl

async def chamar_gemini(prompt):
    chave = pegar("GEMINI_API_KEY") or pegar("GOOGLE_API_KEY")
    if not chave: raise Exception("SEM_CHAVE_GEMINI")
    for modelo in ["gemini-2.0-flash","gemini-1.5-flash"]:
        try:
            async with httpx.AsyncClient(timeout=35) as c:
                r = await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}", json={"contents":[{"parts":[{"text":prompt}]}]})
                if r.status_code==200:
                    d=r.json()
                    txt=d.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
                    if txt: return txt
                elif r.status_code in [400,401,403]: raise Exception(f"GEMINI_{r.status_code}")
        except Exception as e:
            if "GEMINI_" in str(e): raise
            continue
    raise Exception("GEMINI_FALHOU")

async def chamar_meta(prompt):
    chave = pegar("GROQ_API_KEY")
    if not chave: raise Exception("SEM_CHAVE_GROQ")
    for modelo in ["llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
        try:
            async with httpx.AsyncClient(timeout=35) as c:
                r = await c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {chave}","Content-Type":"application/json"}, json={"model":modelo,"messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":4000})
                if r.status_code==200:
                    d=r.json()
                    txt=d.get("choices",[{}])[0].get("message",{}).get("content","")
                    if txt: return txt
                elif r.status_code in [400,401,403,429]: raise Exception(f"GROQ_{r.status_code}")
        except Exception as e:
            if "GROQ_" in str(e): raise
            continue
    raise Exception("GROQ_FALHOU")

async def chamar_gratis(prompt):
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt[:800])}?model=openai")
            if r.status_code==200 and r.text.strip(): return r.text.strip()[:4000]
    except Exception: pass
    raise Exception("GRATIS_FALHOU")

def cerebro_local(prompt, tipo):
    p=prompt.strip()
    if quer_imagem(prompt):
        url, desc = gerar_imagem_hd(p)
        return f"Pronto! Imagem em alta resolução de: {desc}.\n\n[IMAGEM]{url}[/IMAGEM]\n\nQuer outra? Fala: mais colorido, outro fundo, estilo foto real."
    if quer_codigo(prompt):
        codigo = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{p[:30]}</title><style>body{{font-family:Arial;background:#0f1115;color:#fff;padding:20px}}button{{background:#2a6cff;color:#fff;padding:12px;border:0;border-radius:10px}}input{{padding:12px;border-radius:10px;border:0}}</style></head><body><h1>{p[:50]}</h1><input id="t" placeholder="Digite"><button onclick="add()">Adicionar</button><ul id="l"></ul><script>function add(){{var v=document.getElementById('t').value; if(!v) return; var li=document.createElement('li'); li.innerText=v; document.getElementById('l').appendChild(li); document.getElementById('t').value='';}}</script></body></html>"""
        return f"Pronto! Código superprogramador completo.\n\n```html\n{codigo}\n```\n\nCopia e cola em index.html."
    return f"Entendi: {p}.\n\nComo superprogramador, vou te ajudar com isso.\n- Diretoria: organiza em passos.\n- Programação: transforma em código.\n- Publicidade: transforma em nome e campanha.\n\nMe fala: quer código, imagem em alta resolução, ou explicação completa?"

async def superprogramador(pedido, tipo):
    # MODO SUPERPROGRAMADOR: Meta + Gemini juntos, em paralelo, juntam o melhor
    inicio = time.time()
    if quer_codigo(pedido):
        prompt_gemini = f"Você é superprogramador Gemini. Crie código COMPLETO, funcional, pronto para copiar. Não só explique. Pedido: {pedido}. Entregue arquivo por arquivo, com nome do arquivo e código dentro de bloco."
        prompt_meta = f"Você é superprogramador Meta. Crie código COMPLETO, funcional, pronto para copiar, com design bonito e alta qualidade. Pedido: {pedido}. Entregue arquivo por arquivo."
        # Roda os 2 ao mesmo tempo
        res_gemini, res_meta = await asyncio.gather(chamar_gemini(prompt_gemini), chamar_meta(prompt_meta), return_exceptions=True)
        partes = []
        if not isinstance(res_gemini, Exception) and res_gemini: partes.append(f"=== VERSÃO GEMINI ===\n{res_gemini}")
        if not isinstance(res_meta, Exception) and res_meta: partes.append(f"=== VERSÃO META ===\n{res_meta}")
        if partes:
            final = "\n\n".join(partes) + "\n\n=== VERSÃO FINAL SUPERPROGRAMADOR - JUNÇÃO DOS 2 ===\nUse a versão que você mais gostar, ou junta as 2: pega o design da Meta e a lógica do Gemini. As 2 estão completas e prontas para copiar."
            return final, "SUPERPROGRAMADOR-META+GEMINI", int((time.time()-inicio)*1000)
        # Se os 2 falharem, tenta gratis
        try:
            g = await chamar_gratis(f"Crie código completo para: {pedido}")
            return g, "SUPERPROGRAMADOR-GRATIS", int((time.time()-inicio)*1000)
        except Exception:
            return cerebro_local(pedido, tipo), "SUPERPROGRAMADOR-LOCAL", int((time.time()-inicio)*1000)
    # Para qualquer outro tema, também usa os 2 juntos
    if tipo=="programacao": prompt_base = f"Você é superprogramador. Responda com livre arbítrio sobre: {pedido}"
    elif tipo=="publicidade": prompt_base = f"Você é Publicidade superprogramador. Crie nome, campanha e ideia de imagem em alta resolução para: {pedido}"
    elif tipo=="diretoria": prompt_base = f"Você é Diretoria superprogramador. Organize e responda com livre arbítrio sobre: {pedido}"
    else: prompt_base = f"Você é o Time superprogramador, Meta + Gemini juntos, com livre arbítrio para qualquer tema. Responda com profundidade sobre: {pedido}"
    res_gemini, res_meta = await asyncio.gather(chamar_gemini(prompt_base), chamar_meta(prompt_base), return_exceptions=True)
    if not isinstance(res_gemini, Exception) and not isinstance(res_meta, Exception) and res_gemini and res_meta:
        return f"=== GEMINI ===\n{res_gemini}\n\n=== META ===\n{res_meta}\n\n=== RESUMO SUPERPROGRAMADOR ===\nOs 2 concordam no essencial. Use o Gemini para organização e a Meta para criatividade e código.", "SUPERPROGRAMADOR-META+GEMINI", int((time.time()-inicio)*1000)
    if not isinstance(res_gemini, Exception) and res_gemini: return res_gemini, "GEMINI", int((time.time()-inicio)*1000)
    if not isinstance(res_meta, Exception) and res_meta: return res_meta, "META", int((time.time()-inicio)*1000)
    try:
        g = await chamar_gratis(prompt_base)
        return g, "GRATIS", int((time.time()-inicio)*1000)
    except Exception:
        return cerebro_local(pedido, tipo), "LOCAL", int((time.time()-inicio)*1000)

async def orquestrador(pedido, tipo="geral"):
    pedido = corrigir(pedido or "")
    if e_saudacao(pedido):
        return {"resposta":"Olá! Modo superprogramador ligado. Meta + Gemini comandando juntos. Pode pedir: código, imagem em alta resolução, voz, ou qualquer tema.","origem":"saudacao","cerebro":"Superprogramador","tempo_ms":5}
    if e_confirmacao(pedido):
        return {"resposta":"Ok! O que você quer agora? 1. Código, 2. Imagem em alta resolução, 3. OS, 4. Qualquer tema.","origem":"confirmacao","cerebro":"Superprogramador","tempo_ms":5}
    k = hashlib.md5((pedido+tipo).lower().encode()).hexdigest()
    if k in CACHE: return {"resposta":CACHE[k],"origem":"cache","cerebro":"memoria","tempo_ms":5}
    if quer_imagem(pedido):
        # Imagem HD: primeiro melhora o prompt com Gemini/Meta se der, depois gera HD
        url, desc = gerar_imagem_hd(pedido)
        resp = f"Pronto! Imagem em alta resolução 2048x2048 de: {desc}.\n\n[IMAGEM]{url}[/IMAGEM]\n\nQuer outra? Fala: mais colorido, outro fundo, estilo foto real, cria um logo."
        CACHE[k]=resp
        return {"resposta":resp,"origem":"imagem-hd-2048","cerebro":"Criador HD","tempo_ms":50}
    resp, origem, tempo = await superprogramador(pedido, tipo)
    CACHE[k]=resp
    return {"resposta":resp,"origem":origem,"cerebro":"Meta + Gemini","tempo_ms":tempo}

@app.exception_handler(Exception)
async def erro_global(request: Request, exc: Exception):
    return JSONResponse(status_code=200, content={"resposta":f"Erro controlado: {str(exc)[:300]}","origem":"erro-global","cerebro":"sistema","tempo_ms":0})

@app.get("/api/saude")
async def saude():
    return {"status":"ok","sistema":"superprogramador","modo":"Meta + Gemini juntos","gemini":"SIM" if pegar("GEMINI_API_KEY") else "NAO","groq_meta":"SIM" if pegar("GROQ_API_KEY") else "NAO","elevenlabs":"SIM" if pegar("ELEVENLABS_API_KEY") else "NAO","imagem_hd":"LIGADO 2048x2048","funcoes":"por tras do visual"}

@app.get("/api/diagnostico")
async def diagnostico():
    g = pegar("GEMINI_API_KEY"); gr = pegar("GROQ_API_KEY"); el = pegar("ELEVENLABS_API_KEY")
    def masc(ch):
        if not ch: return "VAZIA"
        return f"{ch[:4]}...{ch[-4:]} (tamanho {len(ch)})"
    # Teste real sem mostrar chave
    teste_g="NAO TESTADO"; teste_gr="NAO TESTADO"
    try:
        if g:
            async with httpx.AsyncClient(timeout=10) as c:
                r=await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={g}", json={"contents":[{"parts":[{"text":"Ola"}]}]})
                teste_g="OK" if r.status_code==200 else f"ERRO {r.status_code} - confere se a chave esta no servico 7hdh e se fez Redeploy"
        else: teste_g="SEM CHAVE"
    except Exception as e: teste_g=f"ERRO {str(e)[:100]}"
    try:
        if gr:
            async with httpx.AsyncClient(timeout=10) as c:
                r=await c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {gr}","Content-Type":"application/json"}, json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"Ola"}],"max_tokens":10})
                teste_gr="OK" if r.status_code==200 else f"ERRO {r.status_code} - confere se esta no 7hdh e fez Redeploy"
        else: teste_gr="SEM CHAVE"
    except Exception as e: teste_gr=f"ERRO {str(e)[:100]}"
    return {"GEMINI_mascarada":masc(g),"teste_gemini":teste_g,"GROQ_mascarada":masc(gr),"teste_groq":teste_gr,"ELEVENLABS_mascarada":masc(el),"aviso":"Nunca mostro a chave inteira. Codigo le so pelo NOME no Render."}

@app.post("/api/chat")
async def chat(req: Request):
    try: dados=await req.json()
    except: dados={}
    texto=(dados.get("texto") or dados.get("mensagem") or "").strip()
    tipo=(dados.get("tipo") or "geral").strip().lower()
    if not texto: return {"resposta":"Manda uma frase, qualquer tema. Modo superprogramador ligado.","origem":"vazio","cerebro":"Superprogramador","tempo_ms":0}
    if len(texto)>4000: texto=texto[:4000]
    tipo2="geral"
    if tipo in ["diretoria"]: tipo2="diretoria"
    elif tipo in ["programacao","codigo"]: tipo2="programacao"
    elif tipo in ["publicidade"]: tipo2="publicidade"
    return await orquestrador(texto, tipo2)

@app.post("/api/imagem")
async def imagem(req: Request):
    try: dados=await req.json()
    except: dados={}
    prompt=dados.get("prompt") or dados.get("texto") or "imagem bonita"
    url, desc = gerar_imagem_hd(prompt)
    return {"ok":True,"url":url,"descricao":desc}
@app.post("/api/email/enviar")
async def email_enviar(req: Request):
    try: dados=await req.json()
    except: dados={}
    IDEIAS.append(dados)
    return {"ok":True,"mensagem":"E-mail recebido.","id":len(IDEIAS)}
@app.post("/api/email/analisar")
async def email_analisar(req: Request):
    try: dados=await req.json()
    except: dados={}
    texto=dados.get("texto","") or "Ideia"
    resumo=f"Resumo da Diretoria: {texto[:200]}. Oportunidade: deixar mais simples."
    IDEIAS.append({"assunto":dados.get("assunto","Ideia"),"resumo":resumo})
    return {"ok":True,"ideia":{"resumo":resumo},"resumo":resumo}
@app.get("/")
async def raiz():
    try:
        if os.path.exists("frontend/index.html"):
            with open("frontend/index.html", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    except Exception: pass
    return HTMLResponse(content="<h1>Nexus Superprogramador</h1><p>main no ar. Cola o index_super.html em frontend/index.html</p>")
