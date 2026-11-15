"""Explicit, context-local credentials for separate public and private Blob stores."""
import re
from contextlib import contextmanager

from fastapi import HTTPException
from vercel.api import session
from vercel.blob.sync import BlobCredentials, SyncBlobServiceOptions


@contextmanager
def blob_session(token: str | None):
    # The pinned SDK embeds the store ID in read-write tokens. Supplying a
    # credentials factory binds this token to one SDK session using ContextVar;
    # public and private requests never change process-wide environment values.
    match = re.fullmatch(r"vercel_blob_rw_([A-Za-z0-9-]+)_([^\s]+)", (token or "").strip())
    if not match:
        raise HTTPException(503, "Configure uma credencial válida para o armazenamento de ficheiros")
    credentials = BlobCredentials(token=match.group(0), store_id=match.group(1))
    with session(service_options=[SyncBlobServiceOptions(credentials_factory=lambda: credentials)]):
        yield
