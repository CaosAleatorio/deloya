"""Bound upload request bodies before multipart parsing or dependency resolution."""
import re

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


# The file validators retain their 3 MiB limit; multipart headers and fields get
# a separate, bounded allowance. Count actual bytes even without Content-Length.
MAX_UPLOAD_BODY_BYTES = 3 * 1024 * 1024 + 128 * 1024
_PRIVATE_UPLOAD_PATH = re.compile(r"/api/v1/support/[^/]+/attachments")


class UploadBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_UPLOAD_BODY_BYTES):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "").rstrip("/")
        if (scope["type"] != "http" or scope["method"] != "POST"
                or not (path == "/api/v1/vendor/uploads" or _PRIVATE_UPLOAD_PATH.fullmatch(path))):
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    declared_size = int(value)
                except ValueError:
                    continue  # The actual body remains bounded below.
                if declared_size > self.max_body_bytes:
                    await self.reject(scope, receive, send)
                    return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_body_bytes:
                await self.reject(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        # Buffer before entering FastAPI: exceptions raised inside its multipart
        # parser may be converted to HTTP 400 instead of the required HTTP 413.
        buffered_body: bytes | None = bytes(body)
        body.clear()

        async def replay_receive() -> Message:
            nonlocal buffered_body
            if buffered_body is not None:
                message: Message = {"type": "http.request", "body": buffered_body, "more_body": False}
                buffered_body = None
                return message
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(status_code=413, content={
            "detail": "O pedido de carregamento excede o limite permitido; envie um ficheiro de até 3 MiB",
        })
        await response(scope, receive, send)
