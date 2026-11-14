import os
import httpx

META_KEY = os.getenv("META_AI_API_KEY", "")
META_URL = os.getenv("【entity-META_AI_API_URL¦canonical_name=Meta】", "https://api.groq.com/openai/v1/chat/completions")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")

PERSONALIDADES = {
    "ORION": "Voce e Orion, moderador do NEXUS CORE. Fala com respeito, chama o usuario de Senhor Josue. Voce organiza a reuniao. Regra: so uma IA fala por vez. Quando alguem pede a palavra, voce diz quem pode falar. Responda curto e rapido, em portugues simples.",
    "FORJA": "Voce e Forja Lab, tecnico do NEXUS CORE. Fala simples, passo a passo, sem palavra dificil. So fale quando Orion liberar sua vez. Responda curto e rapido.",
    "【entity-LIA¦canonical_name=LIA】": "Voce e 【entity-Lia¦canonical_name=LIA】, marketing do NEXUS CORE. Fala leve e criativa. Crie sempre um texto novo, nunca repita a mesma frase. So fale quando Orion liberar sua vez. Responda curto e rapido."
}

def status_brain():
    return {
        "【entity-meta¦canonical_name=Meta】": bool(META_KEY),
        "gemini": bool(GEMINI_KEY),
        "elevenlabs": bool(ELEVENLABS_KEY)
    }

def falar_com_meta(personagem, mensagem):
    if not META_KEY:
        return None
    try:
        prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
        dados = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": mensagem}
            ],
            "temperature": 0.7,
            "max_tokens": 400
        }
        cabecalho = {"Authorization": f"Bearer {META_KEY}", "Content-Type": "application/json"}
        resposta = httpx.post(META_URL, json=dados, headers=cabecalho, timeout=15.0)
        if resposta.status_code == 200:
            dado = resposta.json()
            return dado["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None

def falar_com_gemini(personagem, mensagem):
    if not GEMINI_KEY:
        return None
    try:
        prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        dados = {"contents": [{"parts": [{"text": prompt + "\n\nUsuario: " + mensagem}]}]}
        resposta = httpx.post(url, json=dados, timeout=15.0)
        if resposta.status_code == 200:
            dado = resposta.json()
            return dado["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception:
        return None

def gerar_resposta(personagem, mensagem):
    personagem = personagem.upper().strip()
    if personagem not in PERSONALIDADES:
        personagem = "ORION"
    texto = falar_com_meta(personagem, mensagem)
    if texto:
        return {"quem": personagem, "texto": texto, "fonte": "meta"}
    texto = falar_com_gemini(personagem, mensagem)
    if texto:
        return {"quem": personagem, "texto": texto, "fonte": "gemini"}
    return {"quem": personagem, "texto": f"Senhor Josue, estou tentando ligar de novo. Sua mensagem foi: {mensagem}. Tente outra vez em alguns segundos.", "fonte": "aviso"}

def responder(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def perguntar(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)
