from contextlib import contextmanager
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from app.core.config import get_settings
from app.models import PrivateAttachment, SupportTicket
from app.services.attachments import MAX_ATTACHMENT_BYTES
from conftest import login


def picture(image_format="PNG"):
    output = BytesIO()
    Image.new("RGB", (12, 12), "blue").save(output, format=image_format)
    return output.getvalue()


def document():
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(30, 30, "Deloya: anexo privado para teste")
    pdf.save()
    return output.getvalue()


@pytest.fixture
def ticket(db, sample):
    value = SupportTicket(user_id=sample["customer"].id, subject="Apoio", message="Pedido de apoio")
    db.add(value)
    db.commit()
    return value


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setattr(get_settings(), "blob_private_read_write_token", "vercel_blob_rw_privatetest_test-secret")
    objects = {}
    calls = []

    def put(path, content, **options):
        assert options["access"] == "private"
        assert options["allow_overwrite"] is False
        calls.append(("put", path, options))
        objects[path] = content
        return SimpleNamespace(pathname=path, url=f"https://privatetest.private.blob.vercel-storage.com/{path}")

    @contextmanager
    def download(path, **options):
        assert options == {"access": "private"}
        calls.append(("get", path, options))
        value = objects[path]
        class Download:
            metadata = SimpleNamespace(status_code=200)

            def __iter__(self):
                return iter([value[:10], value[10:]])
        yield Download()

    def delete(path):
        calls.append(("delete", path, {}))
        objects.pop(path, None)

    monkeypatch.setattr("vercel.blob.sync.put_blob", put)
    monkeypatch.setattr("vercel.blob.sync.stream_blob", download)
    monkeypatch.setattr("vercel.blob.sync.delete_blob", delete)
    return objects, calls


def upload(client, ticket, filename="imagem.png", content=None, content_type="image/png"):
    return client.post(f"/api/v1/support/{ticket.id}/attachments",
                       files={"file": (filename, picture() if content is None else content, content_type)})


def test_private_upload_list_download_and_delete_never_expose_storage_urls(client, sample, password, ticket, storage, db):
    from PIL.PngImagePlugin import PngInfo
    original = BytesIO()
    metadata = PngInfo()
    metadata.add_text("Comment", "personal metadata removed before storage")
    Image.new("RGB", (12, 12), "blue").save(original, format="PNG", pnginfo=metadata)
    login(client, sample["customer"], password)
    response = upload(client, ticket, filename="../../Fotografia de apoio.png", content=original.getvalue() + b"<script>trailing</script>")
    assert response.status_code == 201, response.text
    metadata = response.json()
    assert set(metadata) == {"id", "created_at", "ticket_id", "uploaded_by", "filename", "content_type", "size_bytes"}
    assert metadata["filename"] == "Fotografia de apoio.png"
    assert metadata["uploaded_by"] == str(sample["customer"].id)
    item = db.get(PrivateAttachment, UUID(metadata["id"]))
    assert item.pathname.startswith(f"support/{ticket.id}/")
    assert b"<script>" not in storage[0][item.pathname]
    assert Image.open(BytesIO(storage[0][item.pathname])).info == {}
    listing = client.get(f"/api/v1/support/{ticket.id}/attachments")
    assert listing.json() == {"items": [metadata]}
    assert "blob.vercel-storage" not in response.text + listing.text
    assert "pathname" not in response.text + listing.text
    download = client.get(f"/api/v1/attachments/{item.id}")
    assert download.status_code == 200
    assert download.content == storage[0][item.pathname]
    assert download.headers["cache-control"] == "no-store"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-type"] == "image/png"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert "filename*=UTF-8''Fotografia%20de%20apoio.png" in download.headers["content-disposition"]
    assert client.delete(f"/api/v1/attachments/{item.id}").status_code == 204
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").json() == {"items": []}
    assert item.pathname not in storage[0]
    assert client.get(f"/api/v1/attachments/{item.id}").status_code == 404


@pytest.mark.parametrize("role", ["other", "vendor", "vendor2"])
def test_other_customers_and_vendors_cannot_access_or_mutate_private_ticket(client, sample, password, ticket, storage, role):
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]
    calls_before = len(storage[1])
    login(client, sample[role], password)
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").status_code == 404
    assert upload(client, ticket).status_code == 404
    assert client.get(f"/api/v1/attachments/{attachment_id}").status_code == 404
    assert client.delete(f"/api/v1/attachments/{attachment_id}").status_code == 404
    assert len(storage[1]) == calls_before


def test_private_routes_require_authentication_and_mutations_require_csrf(client, sample, password, ticket, storage):
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").status_code == 401
    assert upload(client, ticket).status_code == 401
    assert client.get(f"/api/v1/attachments/{uuid4()}").status_code == 401
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]
    client.headers.pop("X-CSRF-Token")
    assert upload(client, ticket).status_code == 403
    assert client.delete(f"/api/v1/attachments/{attachment_id}").status_code == 403


def test_admin_can_review_upload_and_delete_on_customer_ticket(client, sample, password, ticket, storage):
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]
    login(client, sample["admin"], password)
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").json()["items"][0]["id"] == attachment_id
    assert client.get(f"/api/v1/attachments/{attachment_id}").status_code == 200
    admin_file = upload(client, ticket, "resposta.pdf", document(), "application/pdf")
    assert admin_file.status_code == 201, admin_file.text
    assert admin_file.json()["uploaded_by"] == str(sample["admin"].id)
    login(client, sample["customer"], password)
    assert client.get(f"/api/v1/attachments/{admin_file.json()['id']}").status_code == 200
    assert client.delete(f"/api/v1/attachments/{admin_file.json()['id']}").status_code == 204
    login(client, sample["admin"], password)
    assert client.delete(f"/api/v1/attachments/{attachment_id}").status_code == 204


@pytest.mark.parametrize("filename,content,content_type,status", [
    ("unsafe.html", b"<html/>", "text/html", 422),
    ("unsafe.svg", b"<svg/>", "image/svg+xml", 422),
    ("spoof.png", b"not a PNG", "image/png", 422),
    ("mismatch.jpg", picture(), "image/jpeg", 422),
    ("mismatch.png", picture(), "image/jpeg", 422),
    ("empty.pdf", b"", "application/pdf", 422),
    ("spoof.pdf", b"%PDF-1.7\nmalformed\n%%EOF", "application/pdf", 422),
    ("truncated.pdf", b"%PDF-1.7\nmalformed", "application/pdf", 422),
    ("huge.png", b"x" * (MAX_ATTACHMENT_BYTES + 1), "image/png", 413),
], ids=["html", "svg", "fake-png", "jpeg-with-png-bytes", "mime-extension-mismatch",
        "empty-pdf", "fake-pdf", "truncated-pdf", "oversized-image"])
def test_private_upload_validates_actual_content(client, sample, password, ticket, storage, filename, content, content_type, status):
    login(client, sample["customer"], password)
    response = upload(client, ticket, filename, content, content_type)
    assert response.status_code == status, response.text
    assert storage[1] == []
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").json() == {"items": []}


@pytest.mark.parametrize("filename,content_type,image_format", [("one.jpg", "image/jpeg", "JPEG"), ("two.webp", "image/webp", "WEBP")])
def test_private_images_support_jpeg_and_webp(client, sample, password, ticket, storage, filename, content_type, image_format):
    login(client, sample["customer"], password)
    response = upload(client, ticket, filename, picture(image_format), content_type)
    assert response.status_code == 201, response.text
    assert response.json()["content_type"] == content_type


def test_encrypted_and_empty_pdf_are_rejected(client, sample, password, ticket, storage):
    from pypdf import PdfReader, PdfWriter
    login(client, sample["customer"], password)
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(document())))
    writer.encrypt("test-only-passphrase")
    content = BytesIO()
    writer.write(content)
    assert upload(client, ticket, "locked.pdf", content.getvalue(), "application/pdf").status_code == 422
    writer = PdfWriter()
    content = BytesIO()
    writer.write(content)
    assert upload(client, ticket, "empty.pdf", content.getvalue(), "application/pdf").status_code == 422
    assert storage[1] == []


def test_private_configuration_is_separate_from_public_store(client, sample, password, ticket, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "blob_read_write_token", "vercel_blob_rw_publictest_test-secret")
    monkeypatch.setattr(settings, "blob_private_read_write_token", None)
    login(client, sample["customer"], password)
    assert client.get(f"/api/v1/support/{ticket.id}/attachments").json() == {"items": []}
    assert upload(client, ticket).status_code == 503
    monkeypatch.setattr(settings, "blob_private_read_write_token", "not-a-valid-token")
    assert upload(client, ticket).status_code == 503


def test_private_download_and_delete_fail_closed_if_config_removed(client, sample, password, ticket, storage, monkeypatch):
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]
    calls_before = len(storage[1])
    monkeypatch.setattr(get_settings(), "blob_private_read_write_token", None)
    assert client.get(f"/api/v1/attachments/{attachment_id}").status_code == 503
    assert client.delete(f"/api/v1/attachments/{attachment_id}").status_code == 503
    assert len(storage[1]) == calls_before
    assert len(client.get(f"/api/v1/support/{ticket.id}/attachments").json()["items"]) == 1


def test_attachment_count_limit_uses_database_metadata(client, sample, password, ticket, storage, db):
    for index in range(10):
        db.add(PrivateAttachment(ticket_id=ticket.id, uploaded_by=sample["customer"].id,
                                pathname=f"support/{ticket.id}/{index}.pdf", filename=f"{index}.pdf",
                                content_type="application/pdf", size_bytes=100))
    db.commit()
    login(client, sample["customer"], password)
    assert upload(client, ticket).status_code == 409
    assert storage[1] == []


def test_storage_errors_preserve_metadata_and_do_not_expose_secrets(client, sample, password, ticket, storage, monkeypatch):
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]

    def fail(*args, **kwargs):
        raise RuntimeError("secret-provider-url-token")

    monkeypatch.setattr("vercel.blob.sync.stream_blob", fail)
    monkeypatch.setattr("vercel.blob.sync.delete_blob", fail)
    monkeypatch.setattr("vercel.blob.sync.put_blob", fail)
    for response in [client.get(f"/api/v1/attachments/{attachment_id}"),
                     client.delete(f"/api/v1/attachments/{attachment_id}"), upload(client, ticket)]:
        assert response.status_code == 502
        assert "secret-provider" not in response.text
    assert len(client.get(f"/api/v1/support/{ticket.id}/attachments").json()["items"]) == 1


@pytest.mark.parametrize("modified", [b"truncated", b"x" * (MAX_ATTACHMENT_BYTES + 1)], ids=["truncated", "oversized"])
def test_changed_or_oversized_storage_object_never_downloads_as_success(client, sample, password, ticket, storage, db, modified):
    login(client, sample["customer"], password)
    attachment_id = upload(client, ticket).json()["id"]
    item = db.get(PrivateAttachment, UUID(attachment_id))
    storage[0][item.pathname] = modified
    assert client.get(f"/api/v1/attachments/{attachment_id}").status_code == 502
