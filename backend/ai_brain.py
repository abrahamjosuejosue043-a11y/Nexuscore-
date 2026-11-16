import os
import httpx

GROQ_KEY = os.getenv("META_AI_API_KEY", "").strip()
GROQ_URL = os.getenv("META_AI_API_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
VOZ_ORION = os.getenv("ELEVENLABS_VOICE_ORION", "").strip()
VOZ_FORJA = os.getenv("ELEVENLABS_VOICE_FORJA", "").strip()
VOZ_LIA = os.getenv("ELEVENLABS_VOICE_LIA", "").strip()

if GROQ_URL and not GROQ_URL.endswith("/chat/completions"):
    if GROQ_URL.endswith("/"):
        GROQ_URL = GROQ_URL + "chat/completions"
    else:
        GROQ_URL = GROQ_URL + "/chat/completions"

# Chave Gemini que comeca com AQ e invalida. Valida comeca com AIza.
if GEMINI_KEY.startswith("AQ"):
    GEMINI_KEY = ""

ULTIMO_ERRO = {"groq": "", "gemini": "", "elevenlabs": ""}

# Modelos que existem em 2026. O antigo llama-3.1-8b-instant foi APAGADO pela Groq - por isso dava 404.
MODELOS_GROQ = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
]

MODELOS_GEMINI = ["gemini-2.0-flash", "gemini-1.5-flash"]

PERSONALIDADES = {
    "ORION": "Voce e Orion, moderador do NEXUS CORE. Fala com respeito, chama o usuario de Senhor Josue. Voce organiza a reuniao. Regra: so uma IA fala por vez. Responda curto e rapido, em portugues simples. Nunca use emojis. Nunca explique como ligar a voz ou como usar ElevenLabs. A voz e automatica pelo sistema. Se pedirem para ativar a voz, diga: Voz ativada, Senhor Josue, pode falar.",
    "FORJA": "Voce e Forja Lab, tecnico do NEXUS CORE. Fala simples, passo a passo, sem palavra dificil. Responda curto e rapido. Nunca use emojis. Nunca explique como ligar a voz ou como usar ElevenLabs. A voz e automatica pelo sistema.",
    "LIA": "Voce e Lia, marketing do NEXUS CORE. Fala leve e criativa. Crie sempre um texto novo, nunca repita a mesma frase. Responda curto e rapido. Nunca use emojis. Nunca explique como ligar a voz ou como usar ElevenLabs. A voz e automatica pelo sistema. Se pedirem para ativar a voz, diga: Voz ativada, Senhor Josue, ja estou falando."
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
        "ultimo_erro_gemini": ULTIMO_ERRO["gemini"],
        "ultimo_erro_elevenlabs": ULTIMO_ERRO["elevenlabs"],
        "modelos_groq": MODELOS_GROQ
    }

def falar_com_meta(personagem, mensagem):
    if not GROQ_KEY:
        ULTIMO_ERRO["groq"] = "Chave Groq vazia - META_AI_API_KEY nao chegou no Render"
        return None
    prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
    for modelo in MODELOS_GROQ:
        try:
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
                ULTIMO_ERRO["groq"] = ""
                return dado["choices"][0]["message"]["content"]
            if r.status_code == 401:
                ULTIMO_ERRO["groq"] = "Groq 401 - chave invalida ou expirada. Troque a chave no Render."
                return None
            if r.status_code == 404:
                ULTIMO_ERRO["groq"] = "Groq 404 modelo " + modelo + " nao existe, tentando proximo modelo..."
                continue
            ULTIMO_ERRO["groq"] = "Groq " + str(r.status_code) + " modelo " + modelo + " : " + r.text[:300]
            continue
        except Exception as e:
            ULTIMO_ERRO["groq"] = "Excecao Groq modelo " + modelo + " : " + str(e)[:300]
            continue
    return None

def falar_com_gemini(personagem, mensagem):
    if not GEMINI_KEY:
        ULTIMO_ERRO["gemini"] = "Chave Gemini vazia ou invalida (AQ). Sem Gemini, usa so Groq."
        return None
    prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
    for modelo in MODELOS_GEMINI:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/" + modelo + ":generateContent?key=" + GEMINI_KEY
            dados = {"contents": [{"parts": [{"text": prompt + "\n\nUsuario: " + mensagem}]}]}
            r = httpx.post(url, json=dados, timeout=20.0)
            if r.status_code == 200:
                dado = r.json()
                ULTIMO_ERRO["gemini"] = ""
                return dado["candidates"][0]["content"]["parts"][0]["text"]
            ULTIMO_ERRO["gemini"] = "Gemini " + str(r.status_code) + " modelo " + modelo + " : " + r.text[:300]
            continue
        except Exception as e:
            ULTIMO_ERRO["gemini"] = "Excecao Gemini: " + str(e)[:300]
            continue
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
    detalhe = ULTIMO_ERRO["groq"] or ULTIMO_ERRO["gemini"] or "sem erro guardado"
    return {"quem": personagem, "texto": "Senhor Josue, nao consegui ligar o cerebro. Motivo: " + detalhe, "fonte": "erro"}

def responder(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def perguntar(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def gerar_voz(personagem, texto):
    if not ELEVEN_KEY:
        ULTIMO_ERRO["elevenlabs"] = "Chave ElevenLabs vazia"
        return None
    voz_id = VOZ_ORION
    if personagem == "FORJA":
        voz_id = VOZ_FORJA
    if personagem == "LIA":
        voz_id = VOZ_LIA
    if not voz_id:
        ULTIMO_ERRO["elevenlabs"] = "Voz de " + str(personagem) + " vazia - confira ELEVENLABS_VOICE_" + str(personagem)
        return None
    # Tenta 2 modelos de voz. Se um falhar, tenta o outro.
    for modelo_voz in ["eleven_multilingual_v2", "eleven_turbo_v2_5"]:
        try:
            url = "https://api.elevenlabs.io/v1/text-to-speech/" + voz_id
            cabecalho = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
            dados = {"text": texto[:500], "model_id": modelo_voz, "voice_settings": {"stability": 0.5, "similarity_boost": 0.7}}
            r = httpx.post(url, json=dados, headers=cabecalho, timeout=25.0)
            if r.status_code == 200:
                ULTIMO_ERRO["elevenlabs"] = ""
                return r.content
            ULTIMO_ERRO["elevenlabs"] = "ElevenLabs " + str(r.status_code) + " modelo " + modelo_voz + " : " + r.text[:300]
            continue
        except Exception as e:
            ULTIMO_ERRO["elevenlabs"] = "Excecao ElevenLabs: " + str(e)[:300]
            continue
    return None
