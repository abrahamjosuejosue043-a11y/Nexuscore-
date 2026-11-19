
"""
ORQUESTRADOR CORRIGIDO
Correcao 1: Saudacao nao vira OS. Se voce falar Ola, Boa tarde, Oi, ele responde Ola e pergunta qual app voce quer.
Correcao 2: Ok, Sim, Beleza sozinho nao vira tarefa. Ele pergunta: Ok, o que voce quer que eu faca agora?
Correcao 3: Se voce falar "Cria um codigo pytom", ele entende que e Python e manda para a Meta.
"""
import time, hashlib, re
from cerebro1_gemini import chamar_gemini
from cerebro2_meta import chamar_meta

_cache = {}

SAUDACOES = ["ola", "olá", "oi", "bom dia", "boa tarde", "boa noite", "boa tard", "e ai", "eai", "hello", "hi"]
CONFIRMACOES = ["ok", "okay", "sim", "beleza", "entendi", "certo", "fechado", "pode ser", "vamos", "dale"]

def _limpo(texto):
    t = texto.lower().strip()
    t = re.sub(r"[^a-z0-9 ]", "", t)
    t = " ".join(t.split())
    return t

def _e_saudacao(pedido):
    t = _limpo(pedido)
    # Saudacao curta, sem palavra de tarefa como cria, app, codigo, OS, campanha
    tem_tarefa = any(p in t for p in ["cria", "criar", "app", "codigo", "os ", "campanha", "ideia", "projeto", "index", "python", "pytom"])
    if tem_tarefa:
        return False
    return t in SAUDACOES or t.startswith("boa tarde") or t.startswith("bom dia") or t.startswith("boa noite") or t == "ola" or t == "oi"

def _e_confirmacao(pedido):
    t = _limpo(pedido)
    return t in CONFIRMACOES and len(t) < 15

def _corrigir_pytom(pedido):
    # Corrige erro de digitacao comum: pytom -> python
    if "pytom" in pedido.lower():
        pedido = pedido.replace("pytom", "python").replace("Pytom", "Python").replace("PYTOM", "PYTHON")
    return pedido

def orquestrador(pedido, tipo="conversa"):
    pedido = _corrigir_pytom(pedido)

    # CORRECAO: Saudacao nao cria OS
    if _e_saudacao(pedido):
        return {"resposta": "Olá! Tudo bem? Me conta em uma frase qual app você quer criar, que eu já organizo. Por exemplo: Quero um app de lista de tarefas.", "origem": "orquestrador-saudacao", "tempo_ms": 5, "cerebro": "Orquestrador"}

    # CORRECAO: Ok sozinho nao cria tarefa
    if _e_confirmacao(pedido):
        return {"resposta": "Ok! O que você quer que eu faça agora? Pode ser: 1. Criar uma Ordem de Serviço, 2. Criar um código, 3. Criar uma campanha. Me fala qual dos 3.", "origem": "orquestrador-confirmacao", "tempo_ms": 5, "cerebro": "Orquestrador"}

    # Memoria rapida
    k = hashlib.md5((pedido + tipo).lower().encode()).hexdigest()
    if k in _cache:
        return {"resposta": _cache[k], "origem": "cache-rapido", "tempo_ms": 5, "cerebro": "memoria"}

    inicio = time.time()
    if tipo in ["codigo", "programacao"]:
        principal, reserva = "META", "GEMINI"
        pergunta = f"Você é a Programação. Crie código de verdade, não só diga que vai criar. Pedido: {pedido}. Entregue o código completo, arquivo por arquivo, com nome do arquivo e código dentro."
    else:
        principal, reserva = "GEMINI", "META"
        pergunta = pedido

    try:
        resposta = chamar_gemini(pergunta) if principal == "GEMINI" else chamar_meta(pergunta)
        origem, cerebro = f"{principal}-ligado", principal
    except Exception as e1:
        try:
            resposta = chamar_gemini(pergunta) if reserva == "GEMINI" else chamar_meta(pergunta)
            origem, cerebro = f"{reserva}-plano-B", reserva
        except Exception as e2:
            resposta = f"Os dois falharam. Erro principal: {e1}. Erro reserva: {e2}. Confere os nomes das chaves no Render."
            origem, cerebro = "erro", "nenhum"

    tempo = int((time.time() - inicio) * 1000)
    _cache[k] = resposta
    if len(_cache) > 100:
        _cache.pop(next(iter(_cache)))
    return {"resposta": resposta, "origem": origem, "tempo_ms": tempo, "cerebro": cerebro}
