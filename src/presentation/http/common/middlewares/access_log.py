import time

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger("app.http.access")


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            if status_code == 0:
                status_code = 500

            method = scope.get("method", "")
            path = scope.get("path", "")
            query = (scope.get("query_string") or b"").decode("ascii", errors="replace")
            client = scope.get("client")
            addr = f"{client[0]}:{client[1]}" if client else ""

            event = "http_request"
            if status_code >= 500:
                logger.error(
                    event,
                    method=method,
                    path=path,
                    query=query,
                    status=status_code,
                    duration_ms=duration_ms,
                    client=addr,
                )
            elif status_code >= 400:
                logger.warning(
                    event,
                    method=method,
                    path=path,
                    query=query,
                    status=status_code,
                    duration_ms=duration_ms,
                    client=addr,
                )
            else:
                logger.info(
                    event,
                    method=method,
                    path=path,
                    query=query,
                    status=status_code,
                    duration_ms=duration_ms,
                    client=addr,
                )
