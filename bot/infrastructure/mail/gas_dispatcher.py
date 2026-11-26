import aiohttp


class GoogleAppsScriptEmailDispatcher:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        webhook_url: str,
        secret_token: str,
    ) -> None:
        self._session = session
        self._webhook_url = webhook_url.strip()
        self._secret_token = secret_token.strip()

    async def send_report(
        self,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        if not self._webhook_url:
            raise ValueError("GAS_WEBHOOK_URL is not configured")

        payload = {
            "secret": self._secret_token,
            "to": recipient_email.strip(),
            "subject": subject,
            "body": body,
        }

        async with self._session.post(
            self._webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            response_text = await response.text()
            if response.status >= 400 or response_text.strip() != "OK":
                raise RuntimeError(
                    f"Google Apps Script error ({response.status}): {response_text}"
                )
