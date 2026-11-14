import os
import httpx

# Chaves - .strip() tira espaço que vem sem querer no Render
GROQ_KEY = os.getenv("META_AI_API_KEY", "").strip()
GROQ_URL = os.getenv("META_AI_API_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
VOZ_ORION = os.getenv("ELEVENLABS_VOICE_ORION", "").strip()
VOZ_FORJA = os.getenv("ELEVENLABS_VOICE_FORJA", "").strip()
VOZ_LIA = os.getenv("ELEVENLABS_VOICE_LIA", "").strip()

# Corrige URL se vier sem o final /chat/completions
if GROQ_URL and not GROQ_URL.endswith("/chat/completions"):
    if GROQ_URL.endswith("/"):
        GROQ_URL = GROQ_URL + "chat/completions"
    else:
        GROQ_URL = GROQ_URL + "/chat/completions"

# Chave Gemini que comeca com AQ nao e valida. Valida comeca com AIza. Se for AQ, ignora.
if GEMINI_KEY.startswith("AQ"):
    GEMINI_KEY = ""

ULTIMO_ERRO = {"groq": "", "gemini": ""}

PERSONALIDADES = {
    "ORION": "Voce e Orion, moderador do NEXUS CORE. Fala com respeito, chama o usuario de Senhor Josue. Voce organiza a reuniao. Regra: so uma IA fala por vez. Responda curto e rapido, em portugues simples.",
    "FORJA": "Voce e Forja Lab, tecnico do NEXUS CORE. Fala simples, passo a passo, sem palavra dificil. Responda curto e rapido.",
    "LIA": "Voce e Lia, marketing do NEXUS CORE. Fala leve e criativa. Crie sempre um texto novo, nunca repita a mesma frase. Responda curto e rapido."
}

def status_brain():
    return {
        "meta": bool(GROQ_KEY),
        "groq": bool(GROQ_KEY),
        "groq_url": GROQ_URL,
        "gemini": bool(GEMINI_KEY),
        "elevenlabs": bool(ELEVEN_KEY),
        "voz_orion": bool(VOZ_ORION),
        "voz_forja": bool(VOZ_FORJA),
        "voz_lia": bool(VOZ_LIA),
        "ultimo_erro_groq": ULTIMO_ERRO["groq"],
        "ultimo_erro_gemini": ULTIMO_ERRO["gemini"]
    }

def _chamar_groq(personagem, mensagem, modelo):
    prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
    dados = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": mensagem}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    cabecalho = {"Authorization": "Bearer " + GROQ_KEY, "Content-Type": "application/json"}
    r = httpx.post(GROQ_URL, json=dados, headers=cabecalho, timeout=20.0)
    if r.status_code == 200:
        dado = r.json()
        return dado["choices"][0]["message"]["content"]
    # Guarda o erro real para aparecer no status
    ULTIMO_ERRO["groq"] = "Groq " + str(r.status_code) + " modelo " + modelo + " : " + r.text[:300]
    return None

def falar_com_meta(personagem, mensagem):
    if not GROQ_KEY:
        ULTIMO_ERRO["groq"] = "Chave GROQ vazia - META_AI_API_KEY nao chegou no Render"
        return None
    try:
        # Modelo novo primeiro, modelo antigo como reserva
        texto = _chamar_groq(personagem, mensagem, "llama-3.3-70b-versatile")
        if texto:
            return texto
        texto = _chamar_groq(personagem, mensagem, "llama-3.1-8b-instant")
        if texto:
            return texto
        return None
    except Exception as e:
        ULTIMO_ERRO["groq"] = "Excecao Groq: " + str(e)[:300]
        return None

def falar_com_gemini(personagem, mensagem):
    if not GEMINI_KEY:
        ULTIMO_ERRO["gemini"] = "Chave Gemini vazia ou invalida (AQ). Sem Gemini, usa so Groq."
        return None
    try:
        prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + GEMINI_KEY
        dados = {"contents": [{"parts": [{"text": prompt + "\n\nUsuario: " + mensagem}]}]}
        r = httpx.post(url, json=dados, timeout=20.0)
        if r.status_code == 200:
            dado = r.json()
            return dado["candidates"][0]["content"]["parts"][0]["text"]
        ULTIMO_ERRO["gemini"] = "Gemini " + str(r.status_code) + " : " + r.text[:300]
        return None
    except Exception as e:
        ULTIMO_ERRO["gemini"] = "Excecao Gemini: " + str(e)[:300]
        return None

def gerar_resposta(personagem, mensagem):
    personagem = str(personagem).upper().strip()
    if personagem not in PERSONALIDADES:
        personagem = "ORION"
    texto = falar_com_meta(personagem, mensagem)
    if texto:
        return {"quem": personagem, "texto": texto, "fonte": "meta"}
    texto = falar_com_gemini(personagem, mensagem)
    if texto:
        return {"quem": personagem, "texto": texto, "fonte": "gemini"}
    # Fallback agora mostra o erro real, nao repete frase cega
    detalhe = ULTIMO_ERRO["groq"] or ULTIMO_ERRO["gemini"] or "sem erro guardado"
    return {"quem": personagem, "texto": "Senhor Josue, nao consegui ligar o cerebro. Motivo: " + detalhe, "fonte": "erro"}

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
    if personagem == "LIA":
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
