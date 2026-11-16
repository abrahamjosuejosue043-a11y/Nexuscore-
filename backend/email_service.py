import os
import smtplib
import socket
import imaplib
import email as email_lib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Forca IPv4 - corrige [Errno 101] Network is unreachable no Render
_orig_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4(*args, **kwargs):
    try:
        res = _orig_getaddrinfo(*args, **kwargs)
        ipv4 = [r for r in res if r[0] == socket.AF_INET]
        if ipv4:
            return ipv4
        return res
    except Exception:
        return _orig_getaddrinfo(*args, **kwargs)
socket.getaddrinfo = _getaddrinfo_ipv4

def _limpa(v):
    return (v or "").strip().replace(" ", "").replace('"', "").replace("'", "")

GMAIL_USER = _limpa(os.getenv("GMAIL_USER", ""))
GMAIL_PASS = _limpa(os.getenv("GMAIL_APP_PASSWORD", ""))
MEU_EMAIL = os.getenv("MEU_EMAIL_PESSOAL", "").strip()

def _decodificar(texto):
    # Decodifica =?UTF-8?Q?... para texto normal
    if not texto:
        return ""
    try:
        partes = decode_header(str(texto))
        saida = ""
        for conteudo, cod in partes:
            if isinstance(conteudo, bytes):
                saida += conteudo.decode(cod or "utf-8", errors="ignore")
            else:
                saida += str(conteudo)
        return saida
    except Exception:
        return str(texto)

def enviar_email(destino, assunto, texto):
    # Se Para vier vazio ou se Assunto vier com @ (usuario confundiu), corrige
    destino = (destino or "").strip()
    assunto = (assunto or "").strip()
    if "@" in assunto and "@" not in destino:
        # Usuario colocou e-mail no campo Assunto - usa como destino
        destino = assunto
        assunto = "NEXUS CORE - Relatorio"
    if not destino:
        destino = MEU_EMAIL
    if not assunto or "@" in assunto:
        assunto = "NEXUS CORE - Relatorio"
    if not GMAIL_USER or not GMAIL_PASS:
        return {"sucesso": False, "erro": "GMAIL_USER ou GMAIL_APP_PASSWORD vazio no Render. Confira Environment."}
    if not destino:
        return {"sucesso": False, "erro": "Sem destino. Preencha Para ou MEU_EMAIL_PESSOAL no Render."}
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.attach(MIMEText(texto or "", "plain", "utf-8"))
    # Tenta 465 SSL primeiro (Render deixa passar), depois 587 TLS
    erros = []
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        return {"sucesso": True, "para": destino, "via": "465 SSL"}
    except Exception as e:
        erros.append("465: " + str(e)[:200])
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        return {"sucesso": True, "para": destino, "via": "587 TLS"}
    except Exception as e:
        erros.append("587: " + str(e)[:200])
    err = " | ".join(erros)
    if "Username and Password not accepted" in err or "535" in err:
        err = "Gmail recusou login. Senha de app errada ou com espaco. Gere outra senha de app de 16 letras no Google, sem espaco, e cole no Render em GMAIL_APP_PASSWORD."
    if "Network is unreachable" in err or "101" in err:
        err = err + " - Render bloqueou SMTP. Tente de novo, agora via 465 SSL."
    return {"sucesso": False, "erro": err[:600]}

def listar_ideias_novas():
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
            assunto = _decodificar(msg.get("Subject", "Sem assunto"))
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
