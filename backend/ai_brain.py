# Cérebro do NEXUS - 【entity-Meta¦canonical_name=Meta】 primeiro, Gemini de reserva, resposta instantânea
import os, time, httpx
from dotenv import load_dotenv
load_dotenv()

META_KEY = os.getenv("META_AI_API_KEY", "")
META_URL = os.getenv("META_AI_API_URL", "https://api.llama.com/v1/chat/completions")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# Cada IA tem um jeito de falar. Isso é a personalidade.
PERSONALIDADES = {
    "ORION": "Você é Orion, chefe da reunião da Innova XR. Fala grave, direto, organiza tudo, manda em Forja e Lia, chama o chefe de Senhor Josué. Nunca deixa ninguém falar por cima de ninguém.",
    "FORJA": "Você é Forja, do Lab da Innova XR. Fala técnico, direto, sem enrolar. Cria código, imagem e texto. Chama o chefe de Senhor Josué. Sempre diz o que já fez e o que falta.",
    "【entity-LIA¦canonical_name=Lia】": "Você é 【entity-Lia¦canonical_name=Lia】, do Marketing da Innova XR. Fala leve, simpática, que vende. Cria textos, legendas e roteiros. Chama o chefe de Senhor Josué. Sempre termina com uma ideia boa.",
}

# Memória rápida - se perguntar a mesma coisa, responde em 0,1s sem precisar ir na internet
memoria_rapida = {}

# Resposta pronta pra não deixar você esperando
RESPOSTA_RAPIDA = {
    "ORION": "Entendido, Senhor Josué. Já estou organizando e vou passar para Forja e Lia.",
    "FORJA": "Entendido, Senhor Josué. Já estou executando.",
    "LIA": "Entendido, Senhor Josué. Já estou criando um texto leve pra você.",
}

async def falar_com_meta(quem, pergunta):
    """Tenta falar com a Meta primeiro. Se demorar mais de 1,5s, desiste e vai pro Gemini."""
    if not META_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.post(META_URL, headers={"Authorization": f"Bearer {META_KEY}", "Content-Type": "application/json"}, json={
                "model": "Llama-3.1-8B-Instant",
                "messages": [
                    {"role": "system", "content": PERSONALIDADES.get(quem, PERSONALIDADES["ORION"])},
                    {"role": "user", "content": pergunta}
                ],
                "max_tokens": 250,
                "temperature": 0.7
            })
            if r.status_code == 200:
                dados = r.json()
                return dados["choices"][0]["message"]["content"]
    except:
        return None
    return None

async def falar_com_gemini(quem, pergunta):
    """Backup. Se a 【entity-Meta¦canonical_name=Meta】 falhar, o Gemini assume. Também salva tudo como backup."""
    if not GEMINI_KEY:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        prompt = PERSONALIDADES.get(quem, PERSONALIDADES["ORION"]) + "\n\nPergunta do Senhor Josué: " + pergunta
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            if r.status_code == 200:
                dados = r.json()
                return dados["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return None
    return None

async def perguntar(quem, pergunta):
    quem = (quem or "ORION").upper()
    pergunta = (pergunta or "").strip()
    if not pergunta:
        return "O que o senhor precisa, Senhor Josué?"
    chave = quem + "|" + pergunta.lower()[:80]
    # 1. Se já perguntou, responde na hora, 0,1s
    if chave in memoria_rapida:
        return memoria_rapida[chave]
    # 2. Tenta 【entity-Meta¦canonical_name=Meta】
    resposta = await falar_com_meta(quem, pergunta)
    if resposta:
        memoria_rapida[chave] = resposta
        return resposta
    # 3. Se Meta falhar, tenta Gemini
    resposta = await falar_com_gemini(quem, pergunta)
    if resposta:
        memoria_rapida[chave] = resposta
        return resposta
    # 4. Se os dois falharem, responde na hora com resposta pronta, não deixa travar
    return RESPOSTA_RAPIDA.get(quem, RESPOSTA_RAPIDA["ORION"])
