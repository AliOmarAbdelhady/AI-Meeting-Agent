"""SendGrid email provider implementation."""

import logging
from typing import Optional

from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import EmailSendError

logger = logging.getLogger(__name__)


class SendGridEmailProvider:
    """Sends emails via the SendGrid API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or (settings.get_sendgrid_api_key() if settings.sendgrid_api_key else None)
        self._from_address = settings.email_from_address
        self._from_name = settings.email_from_name

    async def send_email(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """Send an email via SendGrid. Returns the message ID."""
        if not self._api_key:
            raise EmailSendError("SendGrid API key not configured")

        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, From, To, Content

            sg = sendgrid.SendGridAPIClient(api_key=self._api_key)

            message = Mail(
                from_email=From(self._from_address, self._from_name),
                to_emails=[To(email) for email in to],
                subject=subject,
            )
            message.add_content(Content("text/html", html_body))
            if text_body:
                message.add_content(Content("text/plain", text_body))

            response = sg.client.mail.send.post(request_body=message.get())

            message_id = response.headers.get("X-Message-Id", "unknown")
            logger.info("Email sent via SendGrid: %s → %s (msg_id=%s)", subject, to, message_id)
            return message_id

        except ImportError:
            raise EmailSendError("sendgrid package not installed. Run: pip install sendgrid")
        except Exception as e:
            raise EmailSendError(f"SendGrid error: {e}")
