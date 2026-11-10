import os
class EmailService:
    def __init__(self):
        self.email_atual = str(os.getenv("NEXUS_EMAIL", "") or "")
        self.nome_atual = str(os.getenv("NEXUS_NOME", "CEO Innova XR") or "CEO Innova XR")
    def cadastrar(self, email: str, nome: str = ""):
        self.email_atual = str(email).strip()
        if nome:
            self.nome_atual = str(nome)
        os.environ["NEXUS_EMAIL"] = self.email_atual
        return True
    def enviar_relatorio(self, email: str, conteudo: str):
        email = str(email).strip()
        conteudo = str(conteudo or "")
        smtp_user = str(os.getenv("SMTP_USER", "") or "")
        smtp_pass = str(os.getenv("SMTP_PASS", "") or "")
        if smtp_user and smtp_pass:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText("Relatorio Nexus Core - Innova XR\n\n" + conteudo, _charset="utf-8")
                msg["Subject"] = "Nexus Core - Relatorio da Reuniao"
                msg["From"] = smtp_user
                msg["To"] = email
                with smtplib.SMTP("smtp.gmail.com", 587) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.send_message(msg)
                return {"ok": True, "modo": "real", "mensagem": "Relatorio enviado com sucesso para " + email}
            except Exception as e:
                return {"ok": False, "modo": "erro_smtp", "mensagem": "Erro SMTP: " + str(e)}
        return {"ok": True, "modo": "simulado", "mensagem": "Relatorio pronto para " + email + " (modo simulado). Configure SMTP_USER / SMTP_PASS no Render para envio real."}
