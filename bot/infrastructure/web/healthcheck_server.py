import logging
from types import TracebackType
from typing import Optional, Type

from aiohttp import web


class HealthcheckServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 10000) -> None:
        self._host = host
        self._port = port
        self._runner: Optional[web.AppRunner] = None
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._handle_health)
        app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, host=self._host, port=self._port)
        await site.start()
        self._logger.info(
            "Healthcheck HTTP server listening on %s:%s",
            self._host,
            self._port,
        )

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def __aenter__(self) -> "HealthcheckServer":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.stop()

    @staticmethod
    async def _handle_health(_request: web.Request) -> web.Response:
        return web.Response(text="OK", status=200)
