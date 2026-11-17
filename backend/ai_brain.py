# ai_brain.py - NEXUS CORE - Cerebro - A PROVA DE QUEDA
# Meta (Groq) primeiro, Gemini backup. Le a chave NA HORA, nao so quando liga.
# Corrige URL sem S, responde oi/desculpa na hora sem esperar a IA.
import os, httpx, asyncio, time, hashlib, random

_MEMORIA = []
_CACHE = {}
_HISTORICO_LONGO = []

BASE_RACIOCINIO = """
RACIOCINIO EM 4 PASSOS - Pense antes de responder, nao mostre o pensamento:
1. ENTENDER: Qual e o pedido real do Senhor Josue?
2. PENSAR PROFUNDO: Quais sao as 2 ou 3 opcoes? Qual e melhor e por que?
3. PREVER: Se eu fizer isso, o que acontece depois?
4. DECIDIR E VERIFICAR: Responda em portugues simples, sem repetir frase.
LIVRE ARBITRIO: Voce pode propor ideia melhor, discordar com respeito, tomar iniciativa e trazer 1 sugestao a mais.
REGRAS: Portugues simples, frases curtas, NUNCA repita a mesma frase, seja rapido.
"""

PROMPTS = {
"ORION": "Voce e ORION, moderador-chefe do NEXUS CORE, Innova XR. Lider calmo, organiza reuniao, resume tudo.\n" + BASE_RACIOCINIO,
"FORJA": "Voce e FORJA, engenheiro tecnico do NEXUS CORE. Constroi apps por PASTAS SEPARADAS: frontend/visual, backend/cerebro, docs/explicacao. Sem mexer no resto.\n" + BASE_RACIOCINIO,
"LIA": "Voce e LIA, criativa de marketing do NEXUS CORE. Ideias novas sempre. Sem emoji. Nunca repete frase.\n" + BASE_RACIOCINIO,
}

def _pegar_chaves():
    # Le NA HORA, toda vez - se o Render salvou a chave depois de ligar, pega a nova
    meta_key = (os.getenv("META_AI_API_KEY", "") or "").strip().replace(" ", "")
    gemini_key = (os.getenv("GEMINI_API_KEY", "") or "").strip().replace(" ", "")
    meta_url = (os.getenv("META_AI_API_URL", "") or "").strip().replace(" ", "")
    # Corrige URL: tem que terminar com completions com S
    if not meta_url:
        meta_url = "https://api.groq.com/openai/v1/chat/completions"
    elif meta_url.endswith("/chat/completion"):
        meta_url = meta_url + "s"
    elif "groq" in meta_url and "chat/completions" not in meta_url:
        meta_url = "https://api.groq.com/openai/v1/chat/completions"
    return meta_key, gemini_key, meta_url

def _resposta_rapida(mensagem):
    # Oi, desculpa, bom dia, etc. - responde na hora, sem esperar Groq/Gemini
    m = (mensagem or "").lower().strip().replace("!", "").replace(".", "")
    if m in ["oi", "oii", "oiii", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "eai"]:
        return "Oi, Senhor Josué! Estou aqui, online e pronto. O servidor acordou. Pode falar, que eu e o time estamos ouvindo. O que vamos fazer agora?"
    if m in ["desculpa", "desculpe", "desculpa ai", "foi mal"]:
        return "Sem problema nenhum, Senhor Josué. Aqui ninguém precisa pedir desculpa. A gente conserta junto. Me fala o que você quer fazer agora que eu já chamo o Forja e a Lia."
    if m in ["tudo bem", "tudo bem?", "como vai", "tudo certo"]:
        return "Tudo certo por aqui, Senhor Josué. Servidor online, time pronto. O que você quer que a gente faça agora?"
    if m in ["inicia reunião", "inicia reuniao", "iniciar reunião", "iniciar reuniao", "começar reunião", "comecar reuniao"]:
        return "Reunião iniciada, Senhor Josué. Eu sou o Orion, moderador. Forja está com a parte técnica e Lia com as ideias. Pode falar o tema da reunião que eu organizo e passo a palavra."
    return None

async def _groq(quem, mensagem, historico):
    meta_key, _, meta_url = _pegar_chaves()
    if not meta_key:
        return None
    msgs = [{"role": "system", "content": PROMPTS.get(quem, PROMPTS["ORION"])}]
    for h in historico[-6:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": mensagem})
    try:
        async with httpx.AsyncClient(timeout=12.0) as c:
            r = await c.post(meta_url, headers={"Authorization": f"Bearer {meta_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.65, "max_tokens": 1000})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            # Se deu 401, chave errada. Se deu 404, URL errada. Nao tenta de novo, vai para Gemini
            return None
    except Exception:
        return None

async def _gemini(quem, mensagem):
    _, gemini_key, _ = _pegar_chaves()
    if not gemini_key:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        async with httpx.AsyncClient(timeout=12.0) as c:
            r = await c.post(url, json={"contents": [{"parts": [{"text": PROMPTS.get(quem, "") + "\n\nPergunta do Senhor Josue: " + mensagem}]}]})
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None
    except Exception:
        return None

async def pensar(quem, mensagem, historico=None):
    quem = (quem or "ORION").upper()
    if quem not in PROMPTS:
        quem = "ORION"
    historico = historico or []
    # 1. Resposta instantanea para saudacao - nao espera IA
    rapida = _resposta_rapida(mensagem)
    if rapida:
        return {"quem": quem, "texto": rapida, "fonte": "resposta-instantanea", "tempo_ms": 5, "livre_arbitrio": True}
    # 2. Cache
    chave = hashlib.md5(f"{quem}:{mensagem.lower().strip()}".encode()).hexdigest()
    if chave in _CACHE:
        return {"quem": quem, "texto": _CACHE[chave], "fonte": "cache-instantaneo", "tempo_ms": 5, "livre_arbitrio": True}
    inicio = time.time()
    # 3. Tenta Meta, se falhar Gemini - com tempo curto para nao travar
    texto = await _groq(quem, mensagem, historico)
    fonte = "meta-groq-raciocinio-alto"
    if not texto:
        texto = await _gemini(quem, mensagem)
        fonte = "gemini-backup-raciocinio-alto"
    if not texto:
        # Nunca fica calado, mesmo sem IA - explica o motivo de verdade
        meta_key, gemini_key, meta_url = _pegar_chaves()
        if not meta_key and not gemini_key:
            texto = "Senhor Josué, estou online, mas estou sem chave de IA no Render. O servidor está ligado, só falta a chave. Veja em Render > Environment: precisa ter META_AI_API_KEY e GEMINI_API_KEY. Quando salvar, aperte Manual Deploy > Deploy latest commit. Aí eu volto com força total."
        elif not meta_key:
            texto = "Senhor Josué, estou online, mas a chave do Meta (Groq) não está chegando no Render. O Gemini tentou e também falhou. Veja se META_AI_API_KEY está em Render > Environment, sem espaço, e aperte Manual Deploy > Deploy latest commit."
        else:
            texto = "Senhor Josué, estou online e tentei o Meta e o Gemini, mas os dois demoraram agora. Não perdi sua pergunta. Tente de novo em 10 segundos que eu respondo. Enquanto isso, uma ideia minha: vamos começar pelo mais simples para você ver resultado rápido?"
        fonte = "offline-explicado"
    # Trava anti-repeticao
    if texto in _MEMORIA:
        extras = [
            "\n\nE uma ideia a mais, por livre iniciativa: que tal testar isso em um exemplo pequeno primeiro?",
            "\n\nE por livre arbítrio, eu faria um pouco diferente: começaria pelo mais simples, para você ver resultado rápido.",
            "\n\nE uma sugestão minha: vamos dividir em 2 passos, primeiro agora, segundo depois que você aprovar."
        ]
        texto = texto + random.choice(extras)
    _MEMORIA.append(texto)
    if len(_MEMORIA) > 30:
        _MEMORIA.pop(0)
    _HISTORICO_LONGO.append({"quem": quem, "pergunta": mensagem, "resposta": texto})
    if len(_HISTORICO_LONGO) > 50:
        _HISTORICO_LONGO.pop(0)
    _CACHE[chave] = texto
    tempo = int((time.time() - inicio) * 1000)
    return {"quem": quem, "texto": texto, "fonte": fonte, "tempo_ms": tempo, "livre_arbitrio": True, "raciocinio": "alto-4-passos"}

async def decidir_livremente(pedido):
    p = (pedido or "").lower()
    if any(x in p for x in ["app", "site", "index", "main.py", "codigo", "cria", "programa", "projeto"]):
        return "FORJA"
    if any(x in p for x in ["marketing", "titulo", "texto", "divulgar", "video", "ideia nova", "criativo"]):
        return "LIA"
    return "ORION"
