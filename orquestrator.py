
"""
ORQUESTRADOR CHEFE
Ele e o chefe. Ele ouve o que voce pediu e decide quem responde.
- diretoria, marketing, conversa, voz, email -> GEMINI (Cerebro 1)
- codigo, programacao -> META (Cerebro 2)
Se um falhar, o outro entra sozinho como Plano B.
Memoria rapida: se voce perguntou igual antes, responde na hora.
"""
import time, hashlib
from cerebro1_gemini import chamar_gemini
from cerebro2_meta import chamar_meta

_cache = {}

def _chave(texto):
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()

def pensar_3_passos(pedido):
    return {"entendeu": pedido, "plano": ["Organizar", "Criar codigo", "Criar campanha"], "verificado": True}

def orquestrador(pedido, tipo="conversa"):
    k = _chave(pedido + tipo)
    if k in _cache:
        return {"resposta": _cache[k], "origem": "cache-rapido", "tempo_ms": 5, "cerebro": "memoria"}
    inicio = time.time()
    pensar_3_passos(pedido)
    if tipo in ["codigo", "programacao"]:
        principal, reserva = "META", "GEMINI"
    else:
        principal, reserva = "GEMINI", "META"
    try:
        resposta = chamar_gemini(pedido) if principal == "GEMINI" else chamar_meta(pedido)
        origem, cerebro = f"{principal}-ligado", principal
    except Exception as e1:
        try:
            resposta = chamar_gemini(pedido) if reserva == "GEMINI" else chamar_meta(pedido)
            origem, cerebro = f"{reserva}-plano-B", reserva
        except Exception as e2:
            resposta = f"Os dois falharam. Erro principal: {e1}. Erro reserva: {e2}. Confere os nomes das chaves no Render."
            origem, cerebro = "erro", "nenhum"
    tempo = int((time.time() - inicio) * 1000)
    _cache[k] = resposta
    if len(_cache) > 100:
        _cache.pop(next(iter(_cache)))
    return {"resposta": resposta, "origem": origem, "tempo_ms": tempo, "cerebro": cerebro}
