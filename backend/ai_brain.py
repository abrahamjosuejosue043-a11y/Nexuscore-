import os
import httpx

GROQ_KEY = os.getenv(" META_AI_API_KEY", "")
GROQ_URL = os.getenv("META_AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOZ_ORION = os.getenv("ELEVENLABS_VOICE_ORION", "")
VOZ_FORJA = os.getenv("ELEVENLABS_VOICE_FORJA", "")
VOZ_LIA = os.getenv("ELEVENLABS_VOICE_LIA", "")

PERSONALIDADES = {
    "ORION": "Voce e Orion, moderador do NEXUS CORE. Fala com respeito, chama o usuario de Senhor Josue. Voce organiza a reuniao. Regra: so uma IA fala por vez. Responda curto e rapido, em portugues simples.",
    "FORJA": "Voce e Forja Lab, tecnico do NEXUS CORE. Fala simples, passo a passo, sem palavra dificil. Responda curto e rapido.",
    " 【entity-LIA¦canonical_name=Lia】": "Voce e 【entity-Lia¦canonical_name=Lia】, marketing do NEXUS CORE. Fala leve e criativa. Crie sempre um texto novo, nunca repita a mesma frase. Responda curto e rapido."
}

def status_brain():
    return {
        " meta": bool(GROQ_KEY),
        "gemini": bool(GEMINI_KEY),
        "elevenlabs": bool(ELEVEN_KEY)
    }

def falar_com_meta(personagem, mensagem):
    if not GROQ_KEY:
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
        cabecalho = {"Authorization": "Bearer " + GROQ_KEY, "Content-Type": "application/json"}
        resposta = httpx.post(GROQ_URL, json=dados, headers=cabecalho, timeout=15.0)
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
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + GEMINI_KEY
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
    return {"quem": personagem, "texto": "Senhor Josue, estou tentando ligar de novo. Sua mensagem foi: " + mensagem + ". Tente outra vez em alguns segundos.", "fonte": "aviso"}

def responder(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def perguntar(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def gerar_voz(personagem, texto):
    if not ELEVEN_KEY:
        return None
    voz_id = VOZ_ORION
    if personagem == "FORJA":
        voz_id = VOZ_FORJA
    if personagem == " LIA":
        voz_id = VOZ_LIA
    if not voz_id:
        return None
    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + voz_id
        cabecalho = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
        dados = {"text": texto[:500], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.7}}
        r = httpx.post(url, json=dados, headers=cabecalho, timeout=20.0)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None
