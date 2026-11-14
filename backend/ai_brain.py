# NEXUS CORE - Codigo que liga as chaves novas
import os
import httpx

META_KEY = os.getenv("【entity-META_AI_API_KEY¦canonical_name=Meta】", "")
META_URL = os.getenv("META_AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")

PERSONALIDADES = {
    "ORION": "Voce e Orion, moderador do NEXUS CORE. Fala com respeito, chama o usuario de Senhor Josue, organiza a reuniao, pede a palavra antes de falar.",
    "FORJA": "Voce e Forja Lab, tecnico do NEXUS CORE. Fala simples, explica passo a passo, sem palavra dificil.",
    "【entity-LIA¦canonical_name=Lia】": "Voce e 【entity-Lia¦canonical_name=Lia】, marketing do NEXUS CORE. Fala leve, criativa, cria textos novos, nunca repete a mesma frase."
}

def status_brain():
    return {
        "【entity-meta¦canonical_name=Meta】": bool(META_KEY),
        "gemini": bool(GEMINI_KEY),
        "elevenlabs": bool(ELEVENLABS_KEY)
    }

def falar_com_meta(personagem, mensagem):
    if not META_KEY:
        print("【entity-Meta¦canonical_name=Meta】 sem chave")
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
            "max_tokens": 800
        }
        cabecalho = {
            "Authorization": f"Bearer {META_KEY}",
            "Content-Type": "application/json"
        }
        resposta = httpx.post(META_URL, json=dados, headers=cabecalho, timeout=30.0)
        print(f"Meta status: {resposta.status_code}")
        if resposta.status_code == 200:
            dado = resposta.json()
            return dado["choices"][0]["message"]["content"]
        print(f"Meta erro: {resposta.text[:200]}")
        return None
    except Exception as e:
        print(f"Erro Meta: {e}")
        return None

def falar_com_gemini(personagem, mensagem):
    if not GEMINI_KEY:
        print("Gemini sem chave")
        return None
    try:
        prompt = PERSONALIDADES.get(personagem, PERSONALIDADES["ORION"])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        dados = {
            "contents": [{"parts": [{"text": prompt + "\n\nUsuario: " + mensagem}]}]
        }
        resposta = httpx.post(url, json=dados, timeout=30.0)
        print(f"Gemini status: {resposta.status_code}")
        if resposta.status_code == 200:
            dado = resposta.json()
            return dado["candidates"][0]["content"]["parts"][0]["text"]
        print(f"Gemini erro: {resposta.text[:200]}")
        return None
    except Exception as e:
        print(f"Erro Gemini: {e}")
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
    return {"quem": personagem, "texto": f"Senhor Josue, a Meta e o Gemini estao sem resposta agora. Vou tentar de novo em um minuto. Sua mensagem foi: {mensagem}", "fonte": "aviso"}

def responder(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)

def perguntar(personagem, mensagem):
    return gerar_resposta(personagem, mensagem)
