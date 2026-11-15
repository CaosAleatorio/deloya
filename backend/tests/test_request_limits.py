import asyncio
import json

import pytest
from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_limits import MAX_UPLOAD_BODY_BYTES, UploadBodyLimitMiddleware


UPLOAD_PATHS = ["/api/v1/vendor/uploads", "/api/v1/support/48e1a178-43c4-4f35-a117-9b4153397561/attachments"]


@pytest.fixture(autouse=True)
def clear_test_database():
    """ASGI body limits use an isolated application and require no database."""


def exercise(path, messages, *, headers=(), maximum=32, method="POST"):
    scope = {"type": "http", "method": method, "path": path, "headers": list(headers)}
    pending = iter(messages)
    observed = {"reads": 0, "downstream": False, "sent": []}

    async def receive():
        observed["reads"] += 1
        return next(pending)

    async def send(message):
        observed["sent"].append(message)

    async def downstream(scope, replay_receive, send):
        observed["downstream"] = True
        observed["reads_before_downstream"] = observed["reads"]
        content = await Request(scope, replay_receive).body()
        await Response(content)(scope, replay_receive, send)

    asyncio.run(UploadBodyLimitMiddleware(downstream, max_body_bytes=maximum)(scope, receive, send))
    observed["status"] = next((item["status"] for item in observed["sent"] if item["type"] == "http.response.start"), None)
    observed["body"] = b"".join(item.get("body", b"") for item in observed["sent"] if item["type"] == "http.response.body")
    return observed


@pytest.mark.parametrize("path", UPLOAD_PATHS)
def test_declared_oversize_rejects_without_reading_body_or_invoking_app(path):
    result = exercise(path, [], headers=[(b"content-length", b"33")])
    assert result["status"] == 413
    assert isinstance(json.loads(result["body"])["detail"], str)
    assert result["reads"] == 0
    assert result["downstream"] is False


@pytest.mark.parametrize("path", UPLOAD_PATHS)
@pytest.mark.parametrize("headers", [[], [(b"transfer-encoding", b"chunked")], [(b"content-length", b"1")]])
def test_actual_oversize_rejects_without_parsing_or_consuming_remaining_body(path, headers):
    messages = [
        {"type": "http.request", "body": b"x" * 32, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": True},
        {"type": "http.request", "body": b"must not be read", "more_body": False},
    ]
    result = exercise(path, messages, headers=headers)
    assert result["status"] == 413
    assert result["reads"] == 2
    assert result["downstream"] is False


@pytest.mark.parametrize("path", UPLOAD_PATHS)
def test_exact_body_boundary_is_buffered_completely_and_replayed_unchanged(path):
    messages = [
        {"type": "http.request", "body": b"a" * 17, "more_body": True},
        {"type": "http.request", "body": b"b" * 15, "more_body": False},
    ]
    result = exercise(path + "/", messages)
    assert result["status"] == 200
    assert result["body"] == b"a" * 17 + b"b" * 15
    assert result["reads_before_downstream"] == result["reads"] == 2


@pytest.mark.parametrize("path,method", [
    ("/api/v1/vendor/uploads", "GET"),
    ("/api/v1/vendor/uploads/image-id", "POST"),
    ("/api/v1/support", "POST"),
    ("/api/v1/attachments/attachment-id", "DELETE"),
])
def test_other_routes_and_methods_are_not_buffered(path, method):
    result = exercise(path, [{"type": "http.request", "body": b"x" * 33}], method=method,
                      headers=[(b"content-length", b"33")])
    assert result["status"] == 200
    assert result["reads_before_downstream"] == 0
    assert result["body"] == b"x" * 33


def test_disconnect_does_not_invoke_downstream_with_an_incomplete_body():
    result = exercise(UPLOAD_PATHS[0], [
        {"type": "http.request", "body": b"unfinished", "more_body": True},
        {"type": "http.disconnect"},
    ])
    assert result["downstream"] is False
    assert result["sent"] == []


@pytest.mark.parametrize("path", UPLOAD_PATHS)
def test_fastapi_accepts_a_three_mib_file_and_returns_413_before_its_parser(path):
    app = FastAPI()
    app.add_middleware(UploadBodyLimitMiddleware)
    calls = []

    @app.post(path)
    async def upload(file: UploadFile = File(...)):
        calls.append(file.size)
        return {"size": file.size}

    with TestClient(app) as client:
        response = client.post(path, files={"file": ("photo.png", b"x" * (3 * 1024 * 1024), "image/png")})
        assert response.status_code == 200
        assert response.json() == {"size": 3 * 1024 * 1024}
        # A malformed multipart body would produce 400 if FastAPI saw it first.
        oversized = client.post(path, content=b"x" * (MAX_UPLOAD_BODY_BYTES + 1),
                                headers={"Content-Type": "multipart/form-data; boundary=missing", "Content-Length": "1"})
        assert oversized.status_code == 413
        assert isinstance(oversized.json()["detail"], str)
        assert calls == [3 * 1024 * 1024]
