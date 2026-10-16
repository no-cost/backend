import logging
import smtplib
from email.message import EmailMessage

from settings import VARS

logger = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"noreply@{VARS['main_domain']}"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    context = {"email": to, "mail_subject": subject}
    try:
        with smtplib.SMTP("127.0.0.1", 25) as smtp:
            smtp.send_message(msg)
    except OSError:  # includes smtplib.SMTPException
        logger.exception("sending e-mail '%s' to %s failed", subject, to, extra=context)
        raise

    logger.info("sent e-mail '%s' to %s", subject, to, extra=context)


def send_donor_thank_you(
    to: str, amount: str, currency: str, total: float, has_perks: bool
) -> None:
    perks_note = ""
    if has_perks:
        perks_note = (
            "\n\nYour total donations qualify you for donor perks, "
            "including the ability to link a custom domain to your site."
        )

    send_mail(
        to=to,
        subject=f"Thank you for your donation — {VARS['main_domain']}",
        body=(
            f"Thank you for your donation of {amount} {currency} "
            f"to {VARS['main_domain']}!\n\n"
            f"Your total donated amount is now {total:.2f} EUR."
            f"{perks_note}\n\n"
            f"We really appreciate your support."
        ),
    )
