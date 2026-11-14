from backend.ai_brain import perguntar, gerar_resposta

PERSONALIDADES = ["ORION", "FORJA", "【entity-LIA¦canonical_name=LIA】"]
reuniao_ativa = False
fila_palavra = []
quem_falando = "ORION"

def processar_mensagem(personagem, mensagem):
    global reuniao_ativa, fila_palavra, quem_falando
    personagem = personagem.upper().strip()
    if personagem not in PERSONALIDADES:
        personagem = "ORION"
    texto Baixo = mensagem.lower().strip()

    if "inicia reuniao" in texto_baixo or "iniciar reuniao" in texto_baixo:
        reuniao_ativa = True
        fila_palavra = []
        quem_falando = "ORION"
        return {"quem": "ORION", "texto": "Senhor Josue, reuniao iniciada. Estou com o microfone ligado, ouvindo sempre. Forja e 【entity-Lia¦canonical_name=LIA】, esperem eu liberar a palavra. Quem quiser falar, diga: pedir a palavra.", "fonte": "【entity-meta¦canonical_name=Meta】", "reuniao": True}

    if "encerrar reuniao" in texto_baixo or "encerrar" in texto_baixo:
        reuniao_ativa = False
        fila_palavra = []
        return {"quem": "ORION", "texto": "Senhor Josue, reuniao encerrada. Vou mandar o relatorio por e-mail.", "fonte": "meta", "reuniao": False}

    if texto_baixo == "para" or texto_baixo == "parar":
        return {"quem": "ORION", "texto": "Pausado, Senhor Josue. Diga continua para voltar.", "fonte": "meta"}

    if "pedir a palavra" in texto_baixo:
        if personagem not in fila_palavra:
            fila_palavra.append(personagem)
        if len(fila_palavra) == 1:
            quem_falando = personagem
            return {"quem": "ORION", "texto": f"{personagem}, pode falar agora. So voce fala, as outras esperam.", "fonte": "【entity-meta¦canonical_name=Meta】"}
        return {"quem": "ORION", "texto": f"{personagem}, voce esta na fila. Agora esta falando {quem_falando}. Espere sua vez.", "fonte": "【entity-meta¦canonical_name=Meta】"}

    if reuniao_ativa and personagem != "ORION" and personagem != quem_falando and "pedir a palavra" not in texto_baixo:
        return {"quem": "ORION", "texto": f"{personagem}, pecam a palavra antes de falar. Agora esta falando {quem_falando}. Diga: pedir a palavra.", "fonte": "【entity-meta¦canonical_name=Meta】"}

    resultado = perguntar(personagem, mensagem)
    if fila_palavra and personagem in fila_palavra:
        fila_palavra.remove(personagem)
        if fila_palavra:
            quem_falando = fila_palavra[0]
    return resultado

def processar(personagem, mensagem):
    return processar_mensagem(personagem, mensagem)

def orquestrar(personagem, mensagem):
    return processar_mensagem(personagem, mensagem)

def iniciar_reuniao(mensagem="inicia reuniao"):
    return processar_mensagem("ORION", mensagem)

def pedir_palavra(personagem, mensagem="pedir a palavra"):
    return processar_mensagem(personagem, mensagem)

class Orchestrator:
    def perguntar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)
    def processar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)
    def orquestrar(self, personagem, mensagem):
        return processar_mensagem(personagem, mensagem)
    def pedir_palavra(self, personagem, mensagem="pedir a palavra"):
        return processar_mensagem(personagem, mensagem)

orchestrator = Orchestrator()
