from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import current_user, rate_limit
from app.database.session import get_db
from app.models import PrivateAttachment, SupportTicket
from app.services.attachments import MAX_ATTACHMENT_BYTES, MAX_TICKET_ATTACHMENTS, validate_attachment
from app.services.blob_storage import blob_session
from app.services.commerce import audit
from app.services.presentation import entity

router = APIRouter()


def authorized_ticket(db, user, ticket_id, *, lock=False):
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if user.role != "admin":
        query = query.where(SupportTicket.user_id == user.id)
    if lock:
        query = query.with_for_update()
    ticket = db.scalar(query)
    if not ticket:
        raise HTTPException(404, "Pedido de apoio não encontrado")
    return ticket


def attachment_data(item):
    # Storage paths, URLs and tokens never cross the authenticated API boundary.
    return entity(item, "ticket_id", "uploaded_by", "filename", "content_type", "size_bytes")


@router.get("/support/{ticket_id}/attachments")
def list_attachments(ticket_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    authorized_ticket(db, user, ticket_id)
    items = db.scalars(select(PrivateAttachment).where(PrivateAttachment.ticket_id == ticket_id)
                       .order_by(PrivateAttachment.created_at)).all()
    return {"items": [attachment_data(item) for item in items]}


@router.post("/support/{ticket_id}/attachments", status_code=201)
def upload_attachment(ticket_id: UUID, request: Request, file: UploadFile = File(...),
                      user=Depends(current_user), db: Session = Depends(get_db)):
    authorized_ticket(db, user, ticket_id)
    rate_limit(db, request, f"attachment:{user.id}", 20)
    # Serialize uploads for a ticket so simultaneous requests respect its quota.
    ticket = authorized_ticket(db, user, ticket_id, lock=True)
    count = db.scalar(select(func.count()).select_from(PrivateAttachment)
                      .where(PrivateAttachment.ticket_id == ticket.id))
    if count >= MAX_TICKET_ATTACHMENTS:
        raise HTTPException(409, "Cada pedido de apoio pode ter até 10 anexos")
    token = get_settings().blob_private_read_write_token
    if not token:
        raise HTTPException(503, "Configure o armazenamento privado para enviar anexos")
    filename, content_type, content = validate_attachment(file)
    item_id = uuid4()
    pathname = f"support/{ticket.id}/{item_id.hex}{PurePosixPath(filename).suffix.lower()}"
    from vercel.blob.sync import put_blob
    try:
        with blob_session(token):
            result = put_blob(pathname, content, access="private", content_type=content_type,
                              allow_overwrite=False)
            if result.pathname != pathname:
                raise ValueError("unexpected storage pathname")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "O armazenamento privado não respondeu; tente novamente") from None
    item = PrivateAttachment(id=item_id, ticket_id=ticket.id, uploaded_by=user.id,
                             pathname=pathname, filename=filename, content_type=content_type,
                             size_bytes=len(content))
    db.add(item)
    audit(db, user, "attachment.uploaded", item, {"ticket_id": str(ticket.id)})
    try:
        db.commit()
    except Exception:
        # A failed DB commit must not leave an untracked private object behind.
        db.rollback()
        from vercel.blob.sync import delete_blob
        try:
            with blob_session(token):
                delete_blob(pathname)
        except Exception:
            pass
        raise
    return attachment_data(item)


def authorized_attachment(db, user, attachment_id, *, lock=False):
    query = select(PrivateAttachment).join(SupportTicket, PrivateAttachment.ticket_id == SupportTicket.id)
    query = query.where(PrivateAttachment.id == attachment_id)
    if user.role != "admin":
        query = query.where(SupportTicket.user_id == user.id)
    if lock:
        query = query.with_for_update(of=PrivateAttachment)
    item = db.scalar(query)
    if not item:
        raise HTTPException(404, "Anexo não encontrado")
    return item


@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    item = authorized_attachment(db, user, attachment_id)
    token = get_settings().blob_private_read_write_token
    if not token:
        raise HTTPException(503, "O armazenamento privado de anexos está indisponível")
    from vercel.blob.sync import BlobNotFoundError, stream_blob
    try:
        # Buffer at most 3 MiB before returning headers, so a provider error or
        # changed object never becomes a truncated successful download.
        content = bytearray()
        with blob_session(token), stream_blob(item.pathname, access="private") as download:
            if download.metadata.status_code != 200:
                raise ValueError("unexpected storage status")
            for chunk in download:
                if len(content) + len(chunk) > MAX_ATTACHMENT_BYTES:
                    raise ValueError("attachment exceeds stored size")
                content.extend(chunk)
        if len(content) != item.size_bytes:
            raise ValueError("attachment size mismatch")
    except BlobNotFoundError:
        raise HTTPException(404, "O ficheiro do anexo não foi encontrado") from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Não foi possível descarregar o anexo; tente novamente") from None
    fallback = f"deloya-anexo-{item.id}{PurePosixPath(item.filename).suffix.lower()}"
    return Response(bytes(content), media_type=item.content_type, headers={
        "Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(item.filename, safe='')}",
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'",
    })


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    item = authorized_attachment(db, user, attachment_id, lock=True)
    token = get_settings().blob_private_read_write_token
    if not token:
        raise HTTPException(503, "O armazenamento privado de anexos está indisponível")
    from vercel.blob.sync import BlobNotFoundError, delete_blob
    try:
        with blob_session(token):
            delete_blob(item.pathname)
    except BlobNotFoundError:
        pass  # A missing object can safely have its remaining metadata removed.
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Não foi possível remover o anexo; tente novamente") from None
    audit(db, user, "attachment.deleted", item, {"ticket_id": str(item.ticket_id)})
    db.delete(item)
    db.commit()
    return Response(status_code=204)
