
"""
SERVICO DE E-MAIL
Faz 3 coisas:
1. Enviar e-mail com ideia, print ou foto -> vai para a Diretoria
2. Receber e-mail -> salva com data e hora
3. Analisar e-mail -> Diretoria cria resumo e salva no Banco de Ideias

Nunca coloca a chave de e-mail aqui no codigo. Chave de e-mail so no Render.
Arquivos salvos: emails_nexus.json e ideias_nexus.json
"""
import json, os, time
from orquestrador import orquestrador

ARQ_EMAILS = "emails_nexus.json"
ARQ_IDEIAS = "ideias_nexus.json"

def _ler(arq):
    if not os.path.exists(arq):
        return []
    try:
        with open(arq, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _salvar(arq, lista):
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

def enviar_email_ideia(de, para, assunto, texto, anexos=[]):
    """Voce manda pelo visual: ideia + print ou foto."""
    email = {
        "de": de, "para": para, "assunto": assunto, "texto": texto,
        "anexos": anexos, "data_hora": time.strftime("%d/%m/%Y %H:%M"),
        "tipo": "enviado_pelo_visual"
    }
    lista = _ler(ARQ_EMAILS)
    lista.append(email)
    _salvar(ARQ_EMAILS, lista)
    return {"status": "enviado", "email": email}

def receber_email(de, assunto, texto, anexos=[]):
    """Quando chega um e-mail novo para a ferramenta."""
    email = {
        "de": de, "assunto": assunto, "texto": texto,
        "anexos": anexos, "data_hora": time.strftime("%d/%m/%Y %H:%M"),
        "tipo": "recebido"
    }
    lista = _ler(ARQ_EMAILS)
    lista.append(email)
    _salvar(ARQ_EMAILS, lista)
    return email

def analisar_email_diretoria(email):
    """Diretoria (Gemini) analisa e salva resumo no Banco de Ideias."""
    pergunta = f"Voce e a Diretoria do Nexus Core. Analise este e-mail e crie resumo para o Banco de Ideias. De: {email.get('de')}. Assunto: {email.get('assunto')}. Texto: {email.get('texto')}. Anexos: {email.get('anexos')}. Devolva: titulo, resumo, o que a imagem mostra, oportunidade, prioridade Alta Media ou Baixa, sugestao de proxima Ordem de Servico."
    resultado = orquestrador(pergunta, tipo="diretoria")
    ideia = {
        "titulo": email.get("assunto", "Ideia recebida"),
        "resumo": resultado["resposta"],
        "cerebro": resultado["cerebro"],
        "origem": resultado["origem"],
        "data_hora": time.strftime("%d/%m/%Y %H:%M"),
        "email_original": email,
        "status": "salva_no_banco"
    }
    lista = _ler(ARQ_IDEIAS)
    lista.append(ideia)
    _salvar(ARQ_IDEIAS, lista)
    return ideia

def listar_emails():
    return _ler(ARQ_EMAILS)

def listar_ideias():
    return _ler(ARQ_IDEIAS)
