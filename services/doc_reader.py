"""Document extraction utilities for PDF and DOCX uploads."""

from io import BytesIO

from PyPDF2 import PdfReader
from docx import Document


class DocumentReadError(Exception):
    """Raised when a document cannot be parsed."""


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def is_allowed_filename(filename):
    if not filename or "." not in filename:
        return False
    ext = "." + filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def _read_pdf(file_bytes):
    reader = PdfReader(BytesIO(file_bytes))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def _read_docx(file_bytes):
    doc = Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text).strip()


def extract_text(file_storage):
    """Extract text from uploaded file storage object."""
    filename = file_storage.filename or ""
    if not is_allowed_filename(filename):
        raise DocumentReadError("Only .pdf and .docx files are supported")

    file_bytes = file_storage.read()
    if not file_bytes:
        raise DocumentReadError("Uploaded file is empty")

    ext = "." + filename.rsplit(".", 1)[1].lower()
    try:
        if ext == ".pdf":
            text = _read_pdf(file_bytes)
        else:
            text = _read_docx(file_bytes)
    except Exception as exc:
        raise DocumentReadError(f"Could not parse document: {exc}") from exc

    if not text:
        raise DocumentReadError("Could not extract readable text from document")
    return text
