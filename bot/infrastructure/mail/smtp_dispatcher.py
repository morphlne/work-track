import asyncio
import smtplib
from email.message import EmailMessage


class SmtpEmailDispatcher:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender_email: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender_email = sender_email

    async def send_report(
        self,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        await asyncio.to_thread(
            self._send_sync,
            recipient_email,
            subject,
            body,
        )

    def _send_sync(
        self,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        if not self._username or not self._password or not self._sender_email:
            raise RuntimeError("SMTP credentials are not configured")

        message = EmailMessage()
        message["From"] = self._sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP_SSL(self._host, self._port, timeout=15) as server:
            server.login(self._username, self._password)
            server.send_message(message)
