# ============================================================
# NEXUS CORE - MAIN.PY - LIGA TUDO
# Arquivo para o GitHub: main.py (na raiz, do lado de index.html e orchestrator.py)
# No Render: Start Command = python main.py
#
# O QUE ELE LIGA:
# 1. index.html = CARA DO APP (PASSO 1 - travado, profissional)
# 2. cerebro.js = MIC + BOTÕES + VOZ NO NAVEGADOR (PASSO 2)
# 3. orchestrator.py = CÉREBRO (PASSO 2 - ORION comanda, FORJA executa, LIA promove)
# 4. ElevenLabs = VOZES (via /api/voice, chave só no Render)
# 5. Groq Meta + Gemini backup = INTELIGÊNCIA
#
# SEM main.py, cada arquivo fica solto. COM main.py, vira UM produto só.
# ============================================================
import os
import sys

# Garante que a pasta atual está no caminho
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Tenta importar o cérebro (orchestrator.py)
try:
    import orchestrator as cerebro
    print("NEXUS: orchestrator.py carregado - CEREBRO OK")
except Exception as e:
    print(f"NEXUS: ERRO ao carregar orchestrator.py: {e}")
    cerebro = None

# Se o orchestrator já tem app Flask, usa ele direto - é o mais simples e certo
# Ele já tem / , /perguntar, /api/chat, /api/voice, /lab/criar, /ordem, /campanha, /quadro, /health
if cerebro is not None and hasattr(cerebro, "app"):
    app = cerebro.app
    print("NEXUS: usando app do orchestrator.py - tudo ligado")
else:
    # Fallback: se orchestrator não tiver app, cria um app mínimo aqui
    # Isso só acontece se o orchestrator estiver velho. O novo já tem app.
    from flask import Flask, request, jsonify, send_from_directory, Response

    app = Flask(__name__)

    @app.after_request
    def _no_cache(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/")
    def index():
        try:
            return send_from_directory(".", "index.html")
        except Exception:
            return jsonify({"ok": True, "msg": "NEXUS CORE rodando. Coloque index.html na raiz."})

    @app.route("/cerebro.js")
    def cerebro_js():
        try:
            return send_from_directory(".", "cerebro.js")
        except Exception:
            return jsonify({"erro": "cerebro.js nao encontrado"}), 404

    @app.route("/health")
    def health():
        return jsonify({"ok": True, "versao": "V12 - MAIN.PY LIGANDO TUDO", "cerebro": cerebro is not None})

    @app.route("/perguntar", methods=["POST"])
    def perguntar():
        d = request.get_json(force=True, silent=True) or {}
        pergunta = d.get("pergunta") or d.get("texto") or ""
        destino = d.get("destino") or "coletiva"
        projeto = d.get("projeto") or "Geral"
        if cerebro and hasattr(cerebro, "responder"):
            return jsonify(cerebro.responder(pergunta, destino=destino, projeto=projeto))
        return jsonify({"respostas": [{"quem": "diretoria", "nome": "ORION", "texto": "Estou aqui, Senhor Josue."}]})

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        d = request.get_json(force=True, silent=True) or {}
        pergunta = d.get("pergunta") or d.get("texto") or ""
        quem = d.get("quem") or "coletiva"
        mapa = {"forja": "lab", "lia": "marketing", "orion": "diretoria", "lab": "lab", "marketing": "marketing", "diretoria": "diretoria", "coletiva": "coletiva"}
        destino = mapa.get(str(quem).lower(), "coletiva")
        if cerebro and hasattr(cerebro, "responder"):
            r = cerebro.responder(pergunta, destino=destino, projeto=d.get("projeto") or "Geral")
            if r.get("respostas"):
                prim = r["respostas"][0]
                return jsonify({"quem": prim["nome"], "resposta": prim["texto"], "respostas": r["respostas"]})
        return jsonify({"quem": "ORION", "resposta": "Estou aqui, Senhor Josue."})

    @app.route("/api/voice", methods=["POST"])
    def api_voice():
        d = request.get_json(force=True, silent=True) or {}
        texto = d.get("texto") or ""
        quem = d.get("quem") or "diretoria"
        if cerebro and hasattr(cerebro, "falar_elevenlabs"):
            audio = cerebro.falar_elevenlabs(texto, quem)
            if audio:
                return Response(audio, mimetype="audio/mpeg")
        return jsonify({"erro": "ElevenLabs nao configurado"}), 503

# ---------------- RODA NO RENDER ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    print(f"==========================================")
    print(f"NEXUS CORE V12 - MAIN.PY LIGANDO TUDO")
    print(f"Porta: {port}")
    print(f"Cara do app: index.html")
    print(f"Cerebro: orchestrator.py")
    print(f"Mic + Botoes: cerebro.js")
    print(f"Voz: ElevenLabs via /api/voice")
    print(f"IA: Meta (Groq) comanda, Gemini backup")
    print(f"Orion comanda -> Forja executa -> Lia promove")
    print(f"==========================================")
    app.run(host="0.0.0.0", port=port)
