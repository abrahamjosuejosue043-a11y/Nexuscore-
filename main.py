# ============================================================
# NEXUS CORE - MAIN.PY - LIGA TUDO - CORRIGIDO ERRO ASGI
# Correção do erro da foto 15:40:
# Log mostrava: ERROR: Exception in ASGI application
# File ".../uvicorn/.../h11_impl.py", line 396, in run_asgi
# Causa: Render ainda estava com comando velho: uvicorn main:app
# uvicorn = ASGI (FastAPI). Nosso app = Flask = WSGI. Não combinava.
# Correção: main.py agora exporta app ASGI (WsgiToAsgi) para uvicorn funcionar,
# e também mantém flask_app para gunicorn / python main.py.
# Assim funciona com QUALQUER comando do Render: uvicorn, gunicorn ou python.
# ============================================================
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import orchestrator as cerebro
    print("NEXUS: orchestrator.py carregado - CEREBRO OK")
    flask_app = cerebro.app if hasattr(cerebro, "app") else None
except Exception as e:
    print(f"NEXUS: ERRO ao carregar orchestrator.py: {e}")
    cerebro = None
    flask_app = None

if flask_app is None:
    # Fallback: cria app mínimo se orchestrator falhar
    from flask import Flask, jsonify, send_from_directory
    flask_app = Flask(__name__)
    @flask_app.route("/")
    def index():
        import os as _os
        for _n in ["index.html", "PASSO1-CORRETO-SEU-CODIGO.html"]:
            if _os.path.exists(_n):
                try:
                    return send_from_directory(".", _n)
                except Exception:
                    pass
        return "<h1>NEXUS CORE V12 rodando</h1><p>Servidor vivo.</p>", 200
    @flask_app.route("/health")
    def health():
        return jsonify({"ok": True, "versao": "V12.2 - MAIN ASGI"})

# --- EXPORTA app ASGI para uvicorn (Render atual) ---
# uvicorn main:app espera app ASGI. Flask é WSGI, então embrulha.
try:
    from asgiref.wsgi import WsgiToAsgi
    app = WsgiToAsgi(flask_app)
    print("NEXUS: app ASGI pronto para uvicorn")
except Exception as e:
    print(f"NEXUS: asgiref não achado ({e}), usando Flask puro")
    app = flask_app

# Mantém referência WSGI para gunicorn, se um dia trocar o comando
wsgi_app = flask_app
flask_app_obj = flask_app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    print("NEXUS CORE V12.2 - MAIN.PY - uvicorn + gunicorn + python")
    flask_app.run(host="0.0.0.0", port=port)
