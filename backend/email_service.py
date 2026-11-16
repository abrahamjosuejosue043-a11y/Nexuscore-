import os
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def _limpa(v):
    # Tira espaco, quebra de linha e aspas que vem sem querer no Render
    return (v or "").strip().replace(" ", "").replace('"', "").replace("'", "")

GMAIL_USER = _limpa(os.getenv("GMAIL_USER", ""))
GMAIL_PASS = _limpa(os.getenv("GMAIL_APP_PASSWORD", ""))
MEU_EMAIL = os.getenv("MEU_EMAIL_PESSOAL", "").strip()

def enviar_email(destino, assunto, texto):
    destino = (destino or MEU_EMAIL or "").strip()
    if not GMAIL_USER or not GMAIL_PASS:
        return {"sucesso": False, "erro": "GMAIL_USER ou GMAIL_APP_PASSWORD vazio no Render. Confira Environment."}
    if not destino:
        return {"sucesso": False, "erro": "Sem destino. Preencha Para ou MEU_EMAIL_PESSOAL no Render."}
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = destino
        msg["Subject"] = assunto or "NEXUS CORE - Relatorio"
        msg.attach(MIMEText(texto or "", "plain", "utf-8"))
        # Gmail SMTP real
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        return {"sucesso": True, "para": destino}
    except Exception as e:
        err = str(e)
        # Traduz os erros mais comuns
        if "Username and Password not accepted" in err or "535" in err:
            err = "Gmail recusou login. Senha de app errada ou com espaco. Gere outra senha de app de 16 letras no Google, sem espaco, e cole no Render em GMAIL_APP_PASSWORD."
        elif "Application-specific password" in err:
            err = "Precisa usar senha de app, nao a senha normal do Gmail. Ative 2 etapas e crie senha de app."
        return {"sucesso": False, "erro": err[:500]}

def listar_ideias_novas():
    # Le a caixa nexuscore.innovaxr@gmail.com via IMAP
    if not GMAIL_USER or not GMAIL_PASS:
        return {"quantidade": 0, "ideias": [], "erro": "GMAIL_USER ou GMAIL_APP_PASSWORD vazio"}
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(GMAIL_USER, GMAIL_PASS)
        m.select("INBOX")
        _, dados = m.search(None, "UNSEEN")
        ids = dados[0].split() if dados and dados[0] else []
        ideias = []
        for id_b in ids[-10:]:
            _, dados_msg = m.fetch(id_b, "(RFC822)")
            msg = email_lib.message_from_bytes(dados_msg[0][1])
            assunto = str(msg.get("Subject", "Sem assunto"))
            texto = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            texto = part.get_payload(decode=True).decode("utf-8", errors="ignore")[:800]
                        except Exception:
                            pass
                        break
            else:
                try:
                    texto = msg.get_payload(decode=True).decode("utf-8", errors="ignore")[:800]
                except Exception:
                    texto = str(msg.get_payload())[:800]
            ideias.append({"assunto": assunto, "texto": texto})
        m.close()
        m.logout()
        return {"quantidade": len(ideias), "ideias": ideias}
    except Exception as e:
        return {"quantidade": 0, "ideias": [], "erro": str(e)[:400]}

def enviar_relatorio(texto_relatorio):
    return enviar_email(MEU_EMAIL, "NEXUS CORE - Relatorio", texto_relatorio)
