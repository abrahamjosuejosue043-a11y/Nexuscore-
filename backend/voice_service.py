# voice_service.py - NEXUS CORE - Voz V3 - ElevenLabs PRINCIPAL, Cartesia RESERVA
# Salvo nas ultimas atualizacoes: enfase no ElevenLabs.
# - 1. ElevenLabs primeiro (voz principal)
# - 2. Cartesia depois (reserva, se ElevenLabs falhar)
# - 3. Navegador por ultimo (se os dois falharem, nao trava o servidor)
# Cada um tem sua voz: ORION, FORJA, LIA
# Chaves no Render:
# - ELEVENLABS_API_KEY = sua chave do ElevenLabs
# - ELEVENLABS_VOICE_ORION = voz do Orion
# - ELEVENLABS_VOICE_FORJA = voz do Forja
# - ELEVENLABS_VOICE_LIA = voz da Lia
# - CARTESIA_API_KEY = chave do Cartesia (reserva)
# - CARTESIA_VOICE_ID = voz do Cartesia (reserva)
import os, httpx, base64

def _pegar_voz_elevenlabs(quem):
    # Pega a voz certa para quem esta falando
    quem = (quem or "ORION").upper()
    if quem not in ["ORION", "FORJA", "LIA"]:
        quem = "ORION"
    # Primeiro tenta a voz da pessoa, depois a do Orion, depois a geral
    voz = (os.getenv(f"ELEVENLABS_VOICE_{quem}", "") or "").strip()
    if not voz:
        voz = (os.getenv("ELEVENLABS_VOICE_ORION", "") or "").strip()
    if not voz:
        voz = (os.getenv("ELEVENLABS_VOICE_ID", "") or "").strip()
    return voz

async def gerar_voz(quem, texto):
    texto = (texto or "")[:900]
    if not texto:
        return {"ok": False, "mensagem": "Sem texto para falar"}
    quem = (quem or "ORION").upper()
    # 1. ELEVENLABS PRIMEIRO - Voz principal
    eleven_key = (os.getenv("ELEVENLABS_API_KEY", "") or "").strip()
    voice_id = _pegar_voz_elevenlabs(quem)
    if eleven_key and voice_id:
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                    json={"text": texto, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}})
                if r.status_code == 200:
                    return {"ok": True, "audio_base64": base64.b64encode(r.content).decode(), "fonte": "elevenlabs", "quem": quem, "voz_principal": "elevenlabs"}
                if r.status_code == 401:
                    # Chave errada - nao trava, vai tentar Cartesia
                    print("ElevenLabs 401 - chave invalida. Tentando Cartesia.")
                elif r.status_code == 402:
                    # Sem credito - nao trava, vai tentar Cartesia
                    print("ElevenLabs 402 - sem credito. Tentando Cartesia.")
                else:
                    print(f"ElevenLabs erro {r.status_code}. Tentando Cartesia.")
        except Exception as e:
            print(f"ElevenLabs falhou: {e}. Tentando Cartesia.")
    else:
        print("ElevenLabs sem chave ou sem voz. Tentando Cartesia.")
    # 2. CARTESIA DEPOIS - Reserva
    cartesia_key = (os.getenv("CARTESIA_API_KEY", "") or "").strip()
    if cartesia_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post("https://api.cartesia.ai/tts/bytes",
                    headers={"X-API-Key": cartesia_key, "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"},
                    json={"model_id": "sonic-3", "transcript": texto,
                          "voice": {"mode": "id", "id": (os.getenv("CARTESIA_VOICE_ID", "") or "").strip() or "a0e99841-438c-4a64-b679-ae501e7d6091"},
                          "output_format": {"container": "mp3", "encoding": "mp3", "sample_rate": 44100}})
                if r.status_code == 200:
                    return {"ok": True, "audio_base64": base64.b64encode(r.content).decode(), "fonte": "cartesia", "quem": quem, "voz_principal": "elevenlabs"}
        except Exception:
            pass
    # 3. SEM VOZ EXTERNA - Navegador fala
    return {"ok": False, "mensagem": "Voz externa off, usando voz do navegador", "usar_navegador": True, "quem": quem, "voz_principal": "elevenlabs"}

async def testar_voz():
    # Testa ElevenLabs primeiro
    eleven_key = (os.getenv("ELEVENLABS_API_KEY", "") or "").strip()
    voice_id = _pegar_voz_elevenlabs("ORION")
    if eleven_key and voice_id:
        r = await gerar_voz("ORION", "Voz ElevenLabs ligada, Senhor Josue. Eu sou o Orion.")
        if r.get("ok") and r.get("fonte") == "elevenlabs":
            return {"ok": True, "mensagem": "ElevenLabs LIGADO - voz principal funcionando.", "fonte": "elevenlabs"}
        if r.get("ok") and r.get("fonte") == "cartesia":
            return {"ok": True, "mensagem": "ElevenLabs falhou, mas Cartesia funcionou como reserva.", "fonte": "cartesia"}
        return {"ok": False, "mensagem": "ElevenLabs com chave, mas deu erro. Veja se a chave esta certa e se a voz do Orion esta certa no Render."}
    if eleven_key and not voice_id:
        return {"ok": False, "mensagem": "Falta a voz do ElevenLabs no Render. Coloque ELEVENLABS_VOICE_ORION, ELEVENLABS_VOICE_FORJA e ELEVENLABS_VOICE_LIA."}
    cartesia_key = (os.getenv("CARTESIA_API_KEY", "") or "").strip()
    if cartesia_key:
        return {"ok": False, "mensagem": "ElevenLabs sem chave. Cartesia com chave, vai usar Cartesia como reserva. Coloque ELEVENLABS_API_KEY no Render para voz principal."}
    return {"ok": False, "mensagem": "Sem chave de voz no Render. Coloque ELEVENLABS_API_KEY. Enquanto isso, o navegador fala."}
