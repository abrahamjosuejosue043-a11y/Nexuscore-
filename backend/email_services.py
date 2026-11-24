"""Adaptador de compatibilidade para os serviços de e-mail e ideias do Nexuscore."""
from backend import storage

def listar_emails():
    with storage.connection() as db:
        rows = db.execute("SELECT * FROM email_log ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]

def listar_ideias():
    return storage.ideas()

def salvar_ideia(titulo: str, resumo: str, prioridade: str = "media"):
    if prioridade not in {"alta", "media", "baixa"}:
        raise ValueError("Prioridade inválida.")
    return storage.save_idea(titulo, resumo, prioridade)

def receber_email(*args, **kwargs):
    raise NotImplementedError("A recepção IMAP deve ser chamada pela API autenticada do Nexuscore.")
