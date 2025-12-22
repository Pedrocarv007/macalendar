import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🔐 Credenciais Zoho
SMTP_SERVER = "smtp.zoho.eu"
SMTP_PORT = 587  # TLS

EMAIL_REMETENTE = "thecarv@thecarv.com"
EMAIL_PASSWORD = "5d77iUBJiviV"  # nunca a password normal

EMAIL_DESTINO = "pedrodecarvalho06@gmail.com"

# 📧 Criar mensagem
msg = MIMEMultipart()
msg["From"] = 'noreply@thecarv.com'
msg["To"] = EMAIL_DESTINO
msg["Subject"] = "Teste de envio via Python + Zoho"

corpo = """
Olá 👋

Este é um e-mail enviado via Python usando SMTP do Zoho.
Se recebeste isto, a integração está a funcionar perfeitamente 🚀

— Python
"""

msg.attach(MIMEText(corpo, "plain", "utf-8"))

# 🚀 Enviar email
try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # segurança primeiro
        server.login(EMAIL_REMETENTE, EMAIL_PASSWORD)
        server.send_message(msg)

    print("✅ Email enviado com sucesso!")

except Exception as e:
    print("❌ Erro ao enviar email:")
    print(e)
