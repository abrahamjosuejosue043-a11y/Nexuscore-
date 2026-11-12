# MAIN - aponta para orchestrator (única fonte de verdade)
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orchestrator as cerebro
app = cerebro.asgi_app if hasattr(cerebro, "asgi_app") else cerebro.app
flask_app = cerebro.app
wsgi_app = cerebro.app
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    cerebro.app.run(host="0.0.0.0", port=port)
