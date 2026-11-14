from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from PIL import Image

from app.core.config import get_settings
from app.models import UploadedImage
from conftest import login


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (20, 20), "blue").save(output, format="PNG")
    return output.getvalue()


def enable_blob(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "blob_read_write_token", "test-token-never-sent")
    monkeypatch.setattr(settings, "blob_public_base_url", "https://example.public.blob.vercel-storage.com")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "test-token-never-sent")


def test_missing_blob_configuration_does_not_write_ephemeral_files(client, sample, password):
    login(client, sample["vendor"], password)
    assert client.post("/api/v1/vendor/uploads", files={"file": ("image.png", image_bytes(), "image/png")}).status_code == 503


def test_upload_validates_size_type_content_and_reencodes(client, sample, password, monkeypatch):
    enable_blob(monkeypatch)
    login(client, sample["vendor"], password)
    assert client.post("/api/v1/vendor/uploads", files={"file": ("image.svg", b"<svg/>", "image/svg+xml")}).status_code == 422
    assert client.post("/api/v1/vendor/uploads", files={"file": ("image.png", b"not a PNG", "image/png")}).status_code == 422
    assert client.post("/api/v1/vendor/uploads", files={"file": ("image.png", b"x" * (3 * 1024 * 1024 + 1), "image/png")}).status_code == 413
    calls = []
    def fake_put(path, content, **options):
        calls.append((path, content, options))
        return SimpleNamespace(url=f"https://example.public.blob.vercel-storage.com/{path}", pathname=path)
    monkeypatch.setattr("vercel.blob.sync.put_blob", fake_put)
    response = client.post("/api/v1/vendor/uploads", files={"file": ("valid.png", image_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    assert len(calls) == 1
    assert calls[0][0].startswith(f"stores/{sample['vendor_store'].id}/")
    assert calls[0][2] == {"access": "public", "content_type": "image/webp"}
    assert Image.open(BytesIO(calls[0][1])).format == "WEBP"


def test_upload_ownership_reference_cleanup_and_delete(client, sample, password, db, monkeypatch):
    enable_blob(monkeypatch)
    own = UploadedImage(store_id=sample["vendor_store"].id,
                        url=f"https://example.public.blob.vercel-storage.com/stores/{sample['vendor_store'].id}/one.webp",
                        pathname=f"stores/{sample['vendor_store'].id}/one.webp")
    other = UploadedImage(store_id=sample["vendor2_store"].id,
                          url=f"https://example.public.blob.vercel-storage.com/stores/{sample['vendor2_store'].id}/two.webp",
                          pathname=f"stores/{sample['vendor2_store'].id}/two.webp")
    db.add_all([own, other])
    db.flush()
    sample["vendor_product"].image_url = own.url
    db.commit()
    login(client, sample["vendor"], password)
    deleted = []
    monkeypatch.setattr("vercel.blob.sync.delete_blob", lambda url: deleted.append(url))
    assert client.delete(f"/api/v1/vendor/uploads/{other.id}").status_code == 404
    assert client.delete(f"/api/v1/vendor/uploads/{own.id}").status_code == 409
    sample["vendor_product"].image_url = None
    db.commit()
    assert client.delete(f"/api/v1/vendor/uploads/{own.id}").status_code == 200
    assert deleted == [own.url]
    assert client.delete(f"/api/v1/vendor/uploads/{own.id}").status_code == 404


def test_receipt_is_private_and_marked_demonstrative(client, sample, password):
    login(client, sample["customer"], password)
    client.post("/api/v1/cart", json={"listing_id": str(sample["vendor_product"].id), "quantity": 1})
    order = client.post("/api/v1/orders", json={"delivery_method": "pickup", "idempotency_key": uuid4().hex}).json()
    response = client.get(f"/api/v1/orders/{order['id']}/receipt.pdf")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response.headers["cache-control"] == "no-store"
    login(client, sample["other"], password)
    assert client.get(f"/api/v1/orders/{order['id']}/receipt.pdf").status_code == 404
