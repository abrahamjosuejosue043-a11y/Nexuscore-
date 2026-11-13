# Orquestrador - manda nas 3 IAs e no projeto
from backend.ai_brain import perguntar
import asyncio

class Orchestrator:
    def __init__(self):
        self.tarefas = [
            {"id": 1, "quem": "FORJA", "titulo": "Integrar 【entity-Meta¦canonical_name=Meta】 AI + Gemini + ElevenLabs", "status": "fazendo", "progresso": 80},
            {"id": 2, "quem": "FORJA", "titulo": "Bloqueio de ruído + resposta instantânea", "status": "feito", "progresso": 100},
            {"id": 3, "quem": "【entity-LIA¦canonical_name=Lia】", "titulo": "Copy de lançamento do NEXUS CORE", "status": "fazendo", "progresso": 60},
            {"id": 4, "quem": "LIA", "titulo": "3 posts para Instagram", "status": "todo", "progresso": 0},
            {"id": 5, "quem": "ORION", "titulo": "Roadmap da semana + aprovar entregas", "status": "fazendo", "progresso": 45},
        ]
        self.next_id = 6

    def listar_tarefas(self):
        return self.tarefas

    def adicionar_tarefa(self, quem, titulo, status="todo"):
        quem = (quem or "ORION").upper()
        prog = 100 if status == "feito" else 50 if status == "fazendo" else 0
        t = {"id": self.next_id, "quem": quem, "titulo": titulo.strip(), "status": status, "progresso": prog}
        self.next_id += 1
        self.tarefas.append(t)
        return t

    def mover_tarefa(self, tarefa_id, status):
        for t in self.tarefas:
            if t["id"] == int(tarefa_id):
                t["status"] = status
                t["progresso"] = 100 if status == "feito" else 50 if status == "fazendo" else 0
                return t
        return None

    async def responder_async(self, quem, pergunta):
        # Usa o cérebro Meta / Gemini
        return await perguntar(quem, pergunta)

    def responder(self, quem, pergunta):
        # Versão simples pra quando não dá pra esperar a internet
        q = (pergunta or "").lower()
        if "projeto" in q:
            feitas = len([t for t in self.tarefas if t["status"] == "feito"])
            return f"Senhor Josué, o projeto está com {feitas} de {len(self.tarefas)} prontas. Abra o painel de projeto."
        if "reuni" in q:
            return "Reunião entendida, Senhor Josué. Vou manter todos em turno, sem interrupção."
        return "Entendido, Senhor Josué. Já estou organizando."

orchestrator = Orchestrator()
