import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx
import pytest
from vercel.api import session
from vercel.blob.sync import get_blob, put_blob

from app.services.blob_storage import blob_session


@pytest.fixture(autouse=True)
def clear_test_database():
    """Credential isolation uses mocked provider HTTP, requiring no database."""


def test_public_and_private_sdk_credentials_are_isolated_during_concurrent_requests(monkeypatch):
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "unchanged-process-environment")
    barrier = Barrier(2)
    observed = []

    def operation(access):
        token = f"vercel_blob_rw_{access}test_test-secret"

        def provider(request):
            # Both real SDK requests reach the mocked external transport at once.
            barrier.wait(timeout=10)
            observed.append((access, request.method, request.headers.get("authorization"), str(request.url)))
            expected_auth = None if request.method == "GET" and access == "public" else f"Bearer {token}"
            assert request.headers.get("authorization") == expected_auth
            if request.method == "GET":
                assert request.url.host == f"{access}test.{access}.blob.vercel-storage.com"
                return httpx.Response(200, content=b"private-or-public-content")
            assert request.headers["x-vercel-blob-access"] == access
            url = f"https://{access}test.{access}.blob.vercel-storage.com/file.png"
            return httpx.Response(200, json={"url": url, "downloadUrl": url, "pathname": "file.png",
                                            "contentType": "image/png", "contentDisposition": "attachment",
                                            "etag": "test-etag"})

        with session(httpx_client_factory=lambda: httpx.Client(transport=httpx.MockTransport(provider))):
            with blob_session(token):
                put_blob("file.png", b"bounded-file", access=access, content_type="image/png")
                assert get_blob("file.png", access=access).body == b"private-or-public-content"

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(operation, ["public", "private"]))
    assert len(observed) == 4
    assert os.environ["BLOB_READ_WRITE_TOKEN"] == "unchanged-process-environment"
