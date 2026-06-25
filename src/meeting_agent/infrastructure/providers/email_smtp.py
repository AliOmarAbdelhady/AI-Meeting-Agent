"""SMTP email provider implementation."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import EmailSendError

logger = logging.getLogger(__name__)


class SMTPEmailProvider:
    """Sends emails via SMTP (e.g., Gmail, Outlook, or any SMTP server)."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self._host = host or settings.smtp_host
        self._port = port or settings.smtp_port
        self._username = username or settings.smtp_username
        self._password = password or settings.get_smtp_password()
        self._use_tls = use_tls if use_tls is not None else settings.smtp_use_tls
        self._from_address = settings.email_from_address
        self._from_name = settings.email_from_name

    async def send_email(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """Send an email via SMTP. Returns a synthetic message ID."""
        if not self._host:
            raise EmailSendError("SMTP host not configured")

        try:
            import aiosmtplib

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self._from_name} <{self._from_address}>"
            msg["To"] = ", ".join(to)

            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # aiosmtplib's connect() handles encryption for us, so we must NOT
            # call starttls() ourselves afterwards — doing so raises
            # "Connection already using TLS" because connect() has already
            # upgraded the connection. Specifically:
            #   - Port 465 (implicit TLS / SMTPS): use_tls=True wraps the whole
            #     connection in TLS from the start.
            #   - Port 587/25 (STARTTLS): with start_tls left at its default
            #     (None), connect() opportunistically upgrades via STARTTLS as
            #     soon as the server advertises support.
            implicit_tls = self._use_tls and self._port == 465
            smtp = aiosmtplib.SMTP(
                hostname=self._host,
                port=self._port,
                use_tls=implicit_tls,
            )
            await smtp.connect()

            if self._username and self._password:
                await smtp.login(self._username, self._password)

            await smtp.send_message(msg)
            await smtp.quit()

            message_id = f"smtp-{id(msg)}@{self._host}"
            logger.info("Email sent via SMTP: %s → %s", subject, to)
            return message_id

        except ImportError:
            raise EmailSendError("aiosmtplib not installed. Run: pip install aiosmtplib")
        except Exception as e:
            raise EmailSendError(f"SMTP error: {e}")
