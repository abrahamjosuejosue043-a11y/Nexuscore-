# Orquestrador - quem fala, quando fala, sem repetir, sem Orion falar sozinho
from backend.ai_brain import gerar_resposta

class Orquestrador:
    def __init__(self):
        self.fila = []
        self.ultima_frase = ""
        self.vez_de = "ORION"

    def pedir_palavra(self, quem):
        quem = str(quem).upper().strip()
        if quem not in ["ORION", "FORJA", "LIA"]:
            quem = "FORJA"
        if quem not in self.fila:
            self.fila.append(quem)
        return {"fila": self.fila, "vez_de": self.vez_de, "mensagem": "Pedido de " + quem + " registrado. Orion vai passar a palavra."}

    def responder(self, quem, mensagem):
        quem = str(quem).upper().strip()
        texto_baixo = str(mensagem).lower().strip()
        # Comandos de reuniao
        if "inicia reuniao" in texto_baixo or "iniciar reuniao" in texto_baixo or "inicia reunião" in texto_baixo:
            self.vez_de = "ORION"
            return gerar_resposta("ORION", "Inicie a reuniao cumprimentando o Senhor Josue e explicando que agora as IAs falam uma por vez.")
        if "ligar o cerebro" in texto_baixo or "liga o cerebro" in texto_baixo:
            return gerar_resposta("ORION", "Teste rapido: diga que o cerebro esta ligado e pergunte o que o Senhor Josue quer fazer.")
        # Se alguem pediu palavra, respeita a fila
        if self.fila:
            self.vez_de = self.fila.pop(0)
            quem = self.vez_de
        if quem not in ["ORION", "FORJA", "LIA"]:
            quem = "ORION"
        resp = gerar_resposta(quem, mensagem)
        # Anti-repeticao da Lia e de todos: se vier igual a ultima, pede variacao
        if resp.get("texto") == self.ultima_frase:
            resp = gerar_resposta(quem, mensagem + " - responda de um jeito diferente, com palavras novas, sem repetir a frase anterior.")
        self.ultima_frase = resp.get("texto", "")
        return resp

orchestrator = Orquestrador()
