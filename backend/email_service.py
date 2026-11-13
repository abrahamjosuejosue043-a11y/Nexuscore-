# E-mail do NEXUS - manda relatório pra você, e recebe ideia pra Orion
import os, smtplib, imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()

# Esses dados vêm do Render, não do 【entity-GitHub¦canonical_name=GitHub】
GMAIL_USER = os.getenv("GMAIL_USER", "")  # E-mail do app, ex: nexuscore.innovaxr@gmail.com
GMAIL_SENHA_APP = os.getenv("GMAIL_APP_PASSWORD", "")  # Senha de app que você cria no Passo 2
MEU_EMAIL = os.getenv("MEU_EMAIL_PESSOAL", "")  # Seu e-mail pessoal, pra receber relatório

def enviar_email(para, assunto, corpo):
    """Manda e-mail. Retorna True se foi, False se não tem e-mail configurado."""
    if not GMAIL_USER or not GMAIL_SENHA_APP:
        print(f"[EMAIL] Não configurado. Para: {para} | Assunto: {assunto}")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"NEXUS CORE <{GMAIL_USER}>"
        msg["To"] = para
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(GMAIL_USER, GMAIL_SENHA_APP)
            s.send_message(msg)
        print(f"[EMAIL] Enviado para {para}")
        return True
    except Exception as e:
        print(f"[EMAIL] Erro: {e}")
        return False

def enviar_relatorio_para_voce(resumo):
    """Manda relatório diário pro seu e-mail pessoal."""
    if not MEU_EMAIL:
        return False
    corpo = f"Olá Senhor Josué,\n\nRelatório do NEXUS CORE:\n\n{resumo}\n\nEquipe: Orion, Forja e Lia\nInnova XR"
    return enviar_email(MEU_EMAIL, "Relatório NEXUS CORE - Innova XR", corpo)

def verificar_ideias_novas():
    """Olha a caixa de entrada do e-mail do app e pega as ideias que você mandou.
    A ideia chega primeiro pro Orion, ele lê e passa pro time."""
    ideias = []
    if not GMAIL_USER or not GMAIL_SENHA_APP:
        return ideias
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_SENHA_APP)
        mail.select("INBOX")
        _, dados = mail.search(None, "UNSEEN")
        for num in dados[0].split():
            _, msg_dados = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_dados[0][1])
            assunto = msg.get("Subject", "Sem assunto")
            remetente = msg.get("From", "")
            corpo = ""
            if msg.is_multipart():
                for parte in msg.walk():
                    if parte.get_content_type() == "text/plain":
                        corpo = parte.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                corpo = msg.get_payload(decode=True).decode("utf-8", errors="ignore") if msg.get_payload(decode=True) else ""
            ideias.append({"de": remetente, "assunto": assunto, "texto": corpo[:1000]})
            mail.store(num, "+FLAGS", "\\Seen")
        mail.logout()
    except Exception as e:
        print(f"[EMAIL] Erro ao ler ideias: {e}")
    return ideias
