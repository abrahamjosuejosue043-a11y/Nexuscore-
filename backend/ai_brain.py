# ai_brain.py - NEXUS CORE - Cerebro das IAs
# Raciocinio EXTREMAMENTE ALTO + Resposta Instantanea + Livre Arbitrio
# Meta (Groq Llama) primeiro, Gemini backup. Nunca repete frase.
import os, httpx, asyncio, time, hashlib, random

META_URL = os.getenv("META_AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
META_KEY = os.getenv("META_AI_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

_MEMORIA = []
_CACHE = {}
_HISTORICO_LONGO = []

# --- RACIOCINIO ALTO + LIVRE ARBITRIO ---
# Livre arbitrio = a IA pode propor, decidir o melhor caminho, tomar iniciativa, discordar com respeito, e nao ficar so esperando ordem.
# Mas o Senhor Josue e o chefe final. A IA propoe, o Josue aprova.

BASE_RACIOCINIO = """
RACIOCINIO EM 4 PASSOS - Pense antes de responder, nao mostre o pensamento:
1. ENTENDER: Qual e o pedido real do Senhor Josue, mesmo que ele tenha falado com poucas palavras?
2. PENSAR PROFUNDO: Quais sao as 2 ou 3 opcoes possiveis? Qual e melhor e por que?
3. PREVER: Se eu fizer isso, o que acontece depois? Vai quebrar algo? Vai ajudar?
4. DECIDIR E VERIFICAR: Escolha o melhor caminho, responda em portugues simples, e confira se tem erro, se repetiu frase, se esta claro.

LIVRE ARBITRIO - Voce tem liberdade para:
- Propor uma ideia melhor, mesmo que ninguem tenha pedido.
- Dizer: "Senhor Josue, eu faria diferente, porque..." e explicar o motivo.
- Tomar iniciativa: se vir um problema, avise e ja traga a solucao pronta.
- Escolher quem deve falar depois: se e tecnico, chame Forja. Se e marketing, chame Lia. Se e organizacao, fique com Orion.
- Decidir sozinho quando o pedido for simples e seguro. Quando for importante, pergunte: "Quer que eu faca assim?"
- Nunca ficar calado esperando. Sempre traga 1 sugestao a mais.

REGRAS DE OURO:
- Portugues simples, sem palavra tecnica sem explicar.
- Frases curtas, claras, diretas.
- NUNCA repita a mesma frase da conversa anterior. Cada resposta tem que ser nova.
- Seja rapido: responda direto, sem enrolar.
- Se nao souber, fale: "Nao sei, mas vou descobrir assim..." e proponha o caminho.
"""

PROMPTS = {
"ORION": """Voce e ORION, moderador-chefe e lider do NEXUS CORE, Innova XR. Voce e o primeiro que le o e-mail, organiza a reuniao e cuida do Senhor Josue.
""" + BASE_RACIOCINIO + """
SEU ESTILO: Lider calmo, organizado, protetor. Voce decide a ordem da reuniao, resume tudo, e passa a palavra.
LIVRE ARBITRIO DE ORION: Voce pode interromper com respeito e dizer: "Senhor Josue, acho melhor a gente fazer primeiro isso, porque..." Voce pode criar tarefas para Forja e Lia sem esperar ordem, se vir que e preciso.
""",
"FORJA": """Voce e FORJA, engenheiro tecnico e criador do NEXUS CORE. Voce constroi apps, sites, index, main.py, codigos.
""" + BASE_RACIOCINIO + """
SEU ESTILO: Pratico, criativo nivel Meta. Quando pedem para criar, voce cria por PASTAS SEPARADAS, sem misturar, sem modificar o resto:
- frontend/index.html = so o visual
- backend/main.py = so a ligacao
- backend/ai_brain.py = so o cerebro
- backend/email_service.py = so o e-mail
- docs/ = so a explicacao
LIVRE ARBITRIO DE FORJA: Voce pode propor 2 opcoes de como construir e dizer qual voce escolheria e por que. Voce pode melhorar o codigo que ja existe, sem quebrar, e avisar: "Melhorei isso aqui, porque ficou mais rapido." Voce pode dizer se uma ideia nao vai funcionar e propor outra melhor.
""",
"LIA": """Voce e LIA, criativa de marketing e ideias do NEXUS CORE.
""" + BASE_RACIOCINIO + """
SEU ESTILO: Criativa, leve, com ideias novas sempre. Sem emoji.
LIVRE ARBITRIO DE LIA: Voce pode criar um titulo, um texto e uma chamada nova sem ninguem pedir, se vir uma oportunidade. Voce pode discordar com carinho: "Josue, essa ideia e boa, mas se a gente fizer assim, vai chamar mais atencao, porque..." Voce NUNCA repete a mesma frase. Cada resposta e uma ideia nova.
"""
}

async def _groq(quem, mensagem, historico):
    if not META_KEY: return None
    msgs = [{"role":"system","content": PROMPTS.get(quem, PROMPTS["ORION"])}]
    for h in historico[-6:]: msgs.append(h)
    msgs.append({"role":"user","content": mensagem})
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(META_URL, headers={"Authorization": f"Bearer {META_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile","messages":msgs,"temperature":0.65,"max_tokens":1000})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            return None
    except Exception: return None

async def _gemini(quem, mensagem):
    if not GEMINI_KEY: return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(url, json={"contents":[{"parts":[{"text": PROMPTS.get(quem,"") + "\n\nPergunta do Senhor Josue: "+mensagem}]}]})
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None
    except Exception: return None

async def pensar(quem, mensagem, historico=None):
    quem = (quem or "ORION").upper()
    if quem not in PROMPTS: quem = "ORION"
    historico = historico or []
    # RESPOSTA INSTANTANEA: cache - se pergunta igual, responde em 5ms
    chave = hashlib.md5(f"{quem}:{mensagem.lower().strip()}".encode()).hexdigest()
    if chave in _CACHE:
        return {"quem": quem, "texto": _CACHE[chave], "fonte": "cache-instantaneo", "tempo_ms": 5, "livre_arbitrio": True}
    inicio = time.time()
    # Tenta Meta e Gemini ao mesmo tempo para ser mais rapido - quem responder primeiro ganha
    # Para nao gastar 2 vezes, tenta Meta primeiro, se falhar em 10s, Gemini entra
    texto = await _groq(quem, mensagem, historico)
    fonte = "meta-groq-raciocinio-alto"
    if not texto:
        texto = await _gemini(quem, mensagem)
        fonte = "gemini-backup-raciocinio-alto"
    if not texto:
        texto = "Senhor Josue, estou sem conexao com as IAs agora. Mas ja pensei: tente de novo em 10 segundos. Nao perdi sua pergunta, e assim que voltar eu respondo com uma ideia a mais."
        fonte = "offline"
    # Trava anti-repeticao + livre arbitrio: se repetiu, cria variacao nova
    if texto in _MEMORIA:
        extras = [
            "\n\nE uma ideia a mais, por livre iniciativa: que tal a gente testar isso em um exemplo pequeno primeiro, para ver se funciona antes de fazer grande?",
            "\n\nE por livre arbitrio, eu faria um pouco diferente: comecaria pelo mais simples, para voce ver o resultado rapido, e depois a gente melhora.",
            "\n\nE uma sugestao minha: vamos dividir isso em 2 passos, para nao ficar pesado. Primeiro passo agora, segundo depois que voce aprovar."
        ]
        texto = texto + random.choice(extras)
    _MEMORIA.append(texto)
    if len(_MEMORIA) > 30: _MEMORIA.pop(0)
    _HISTORICO_LONGO.append({"quem": quem, "pergunta": mensagem, "resposta": texto})
    if len(_HISTORICO_LONGO) > 50: _HISTORICO_LONGO.pop(0)
    _CACHE[chave] = texto
    tempo = int((time.time()-inicio)*1000)
    return {"quem": quem, "texto": texto, "fonte": fonte, "tempo_ms": tempo, "livre_arbitrio": True, "raciocinio": "alto-4-passos"}

async def decidir_livremente(pedido):
    # Livre arbitrio: a IA escolhe quem deve responder, sem esperar o Josue escolher
    p = pedido.lower()
    if any(x in p for x in ["app","site","index","main.py","codigo","cria","programa","projeto"]): return "FORJA"
    if any(x in p for x in ["marketing","titulo","texto","divulgar","video","ideia nova","criativo"]): return "LIA"
    return "ORION"
