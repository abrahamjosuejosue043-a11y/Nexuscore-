import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NEXUS CORE • Innova XR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chaves configuradas nas Variáveis de Ambiente do Render (nunca expostas no HTML)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")       # Roda os modelos Meta Llama 3.3 com velocidade instantânea
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")   # Backup oficial Google Gemini
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")   # Vozes realistas

# Personalidades do Conselho Innova XR
PERSONAS = {
    "ORION": (
        "Você é ORION, Diretor Executivo de Estratégia da Innova XR. "
        "Fale sempre em português do Brasil, tratando o usuário como 'Senhor Josué'. "
        "Seja direto, estratégico, analítico e conciso (máximo 3 frases curtas para fluir bem em áudio)."
    ),
    "FORJA": (
        "Você é FORJA, Engenheiro Chefe de Software e Laboratório da Innova XR. "
        "Fale em português do Brasil, chamando o usuário de 'Senhor Josué'. "
        "Foque em código, arquitetura, automação e soluções técnicas práticas. Seja objetivo (máximo 3 frases)."
    ),
    "LIA": (
        "Você é LIA, Diretora de Marketing, Comunicação e Expansão da Innova XR. "
        "Fale em português do Brasil, chamando o usuário de 'Senhor Josué'. "
        "Foque em copywriting, vendas, posicionamento e divulgação criativa. Seja persuasiva e breve (máximo 3 frases)."
    ),
    "COLETIVA": (
        "Você coordena uma reunião executiva da Innova XR com ORION (Estratégia), FORJA (Engenharia) e LIA (Marketing) "
        "para o Senhor Josué. Responda de forma integrada e objetiva em no máximo 4 frases."
    )
}

# IDs de vozes da ElevenLabs (você pode trocar pelos IDs que preferir na sua conta)
VOZES_ELEVEN = {
    "ORION": "pNInz6obpgDQGcFmaJgB",  # Adam (Voz masculina grave e executiva)
    "FORJA": "TxGEqnHWrfWFTfGW9XjX",  # Josh (Voz masculina firme e técnica)
    "LIA":   "EXAVITQu4vr4xnSDxMaL",  # Bella (Voz feminina clara e articulada)
}

class ChatRequest(BaseModel):
    quem: str = "ORION"
    modo: str = "SOLO"
    pergunta: str

class VoiceRequest(BaseModel):
    quem: str = "ORION"
    texto: str

async def chamar_meta_llama(sistema: str, pergunta: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("Chave GROQ_API_KEY não configurada.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": pergunta}
        ],
        "temperature": 0.6,
        "max_tokens": 300
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

async def chamar_gemini_backup(sistema: str, pergunta: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("Chave GEMINI_API_KEY não configurada.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"parts": [{"text": pergunta}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 300}
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

@app.get("/", response_class=HTMLResponse)
async def servir_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def processar_chat(req: ChatRequest):
    quem = req.quem.upper() if req.quem.upper() in PERSONAS else "ORION"
    chave_persona = "COLETIVA" if req.modo.upper() == "COLETIVA" else quem
    sistema = PERSONAS[chave_persona]

    motor_usado = "META-LLAMA"
    try:
        # 1ª Tentativa: Meta Llama (Cérebro Principal)
        resposta = await chamar_meta_llama(sistema, req.pergunta)
    except Exception as e_meta:
        print(f"[AVISO] Meta Llama falhou ({e_meta}). Acionando backup Gemini...")
        try:
            # 2ª Tentativa: Google Gemini (Backup Automático)
            resposta = await chamar_gemini_backup(sistema, req.pergunta)
            motor_usado = "GEMINI-BACKUP"
        except Exception as e_gem:
            print(f"[ERRO] Falha total nas APIs: {e_gem}")
            resposta = "Senhor Josué, houve uma instabilidade na conexão com os servidores externos. Verifique as chaves de API."
            motor_usado = "OFFLINE"

    return {
        "quem": quem,
        "motor": motor_usado,
        "resposta": resposta
    }

@app.post("/api/voice")
async def gerar_voz(req: VoiceRequest):
    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=503, detail="Chave de voz não configurada.")

    voice_id = VOZES_ELEVEN.get(req.quem.upper(), VOZES_ELEVEN["ORION"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": req.texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Erro ao sintetizar voz.")
        return Response(content=resp.content, media_type="audio/mpeg")
