import smtplib
from email.message import EmailMessage

from settings import VARS


def send_mail(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"noreply@{VARS['main_domain']}"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("127.0.0.1", 25) as smtp:
        smtp.send_message(msg)
