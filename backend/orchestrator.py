# NEXUS CORE - Organizador que deixa o cerebro falar, sem frase pronta
from backend.ai_brain import perguntar, gerar_resposta, status_brain

PERSONALIDADES = ["ORION", "FORJA", " LIA"]

def processar_mensagem(personagem, mensagem):
    personagem = personagem.upper().strip()
    if personagem not in PERSONALIDADES:
        personagem = "ORION"
    resultado = perguntar(personagem, mensagem)
    return resultado

def processar(personagem, mensagem):
    return processar_mensagem(personagem, mensagem)

def orquestrar(personagem, mensagem):
    return processar_mensagem(personagem, mensagem)

def iniciar_reuniao(mensagem="Inicia reuniao"):
    return processar_mensagem("ORION", mensagem)

def pedir_palavra(personagem, mensagem):
    return processar_mensagem(personagem, mensagem)

class Orchestrator:
    def perguntar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)
    def processar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)
    def orquestrar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)

# Nome com letra minuscula que o main.py procura
orchestrator = Orchestrator()
