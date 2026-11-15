"""Validate bounded attachments and deliver them only through authenticated routes."""
import re
import warnings
from io import BytesIO
from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader


MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024
MAX_TICKET_ATTACHMENTS = 10
FILE_FORMATS = {
    "image/jpeg": ({".jpg", ".jpeg"}, "JPEG"),
    "image/png": ({".png"}, "PNG"),
    "image/webp": ({".webp"}, "WEBP"),
    "application/pdf": ({".pdf"}, None),
}


def validate_attachment(file: UploadFile) -> tuple[str, str, bytes]:
    filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
    filename = "".join(char for char in filename if ord(char) >= 32 and ord(char) != 127).strip()
    if not filename or len(filename) > 180:
        raise HTTPException(422, "O nome do ficheiro deve ter entre 1 e 180 caracteres")
    content_type = file.content_type or ""
    suffix = PurePosixPath(filename).suffix.lower()
    if content_type not in FILE_FORMATS or suffix not in FILE_FORMATS[content_type][0]:
        raise HTTPException(422, "Apenas ficheiros JPEG, PNG, WebP ou PDF são permitidos")
    content = file.file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(413, "O anexo deve ter no máximo 3 MB")
    if not content:
        raise HTTPException(422, "O ficheiro está vazio")
    if content_type == "application/pdf":
        # Parse the bounded PDF structure without rendering/decompressing page
        # contents. PDFs remain downloads, never inline browser documents.
        try:
            if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)[\r\n]", content) or not content.rstrip().endswith(b"%%EOF"):
                raise ValueError("invalid PDF envelope")
            pdf = PdfReader(BytesIO(content), strict=True)
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 100:
                raise ValueError("encrypted, empty or oversized page tree")
            for page in pdf.pages:
                _ = page.mediabox
        except Exception:
            raise HTTPException(422, "PDF inválido; envie um documento sem palavra-passe, com até 100 páginas") from None
        return filename, content_type, content
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(content))
            image_format = FILE_FORMATS[content_type][1]
            if image.format != image_format or image.width * image.height > 20_000_000:
                raise ValueError("unexpected image format or dimensions")
            image.load()
            image = image.convert("RGB")
            image.info.clear()
            output = BytesIO()
            # Re-encoding discards metadata and trailing/polyglot content.
            image.save(output, format=image_format)
            content = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise HTTPException(422, "Conteúdo de imagem inválido") from None
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(413, "A imagem processada excede o limite de 3 MB")
    return filename, content_type, content
