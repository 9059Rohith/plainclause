"""Bounded, structure-preserving extraction of local legal documents."""
from dataclasses import dataclass
from io import BytesIO
import re
import textwrap
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from pypdf import PdfReader

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_TEXT_CHARS = 600_000
MAX_ZIP_UNCOMPRESSED = 30 * 1024 * 1024
MAX_OCR_PAGES = 50
NUMBERED_HEADING = re.compile(r"^(?:(?:section|article|clause)\s+)?\d+(?:\.\d+)*[.)]?\s+\S", re.I)
NUMBERED_CLAUSE = re.compile(r"^(?:(?:section|article|clause)\s+)?(\d+(?:\.\d+)*[.)]?)\s+(.+)$", re.I)
OPERATIVE_WORD = re.compile(r"\b(?:shall|must|may|will|can|cannot|agrees?|requires?|prohibits?|entitled|due)\b", re.I)
UPPER_HEADING = re.compile(r"^[A-Z][A-Z\s/&-]{3,}$")
ENGLISH_WORDS = {"the", "and", "or", "of", "to", "in", "for", "with", "by", "is", "are", "shall", "must", "may", "this", "that", "party", "agreement", "notice", "payment", "days"}
OTHER_LANGUAGE_WORDS = {"el", "la", "los", "las", "del", "debe", "pagar", "arrendatario", "contrato", "plazo", "le", "les", "des", "doit", "payer", "locataire", "contrat", "der", "die", "das", "und", "muss", "mieter", "vertrag", "il", "deve", "pagare", "conduttore", "locatario"}


class UploadError(ValueError):
    pass


@dataclass(frozen=True)
class Section:
    heading: str
    text: str
    page: int = 1


def _validate_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").strip()
    if not text:
        raise UploadError("This document contains no readable text.")
    if len(text) > MAX_TEXT_CHARS:
        raise UploadError("The extracted text is too long (limit: 600,000 characters).")
    if len(re.findall(r"[A-Za-z]", text)) < 12:
        raise UploadError("There is too little readable English text to analyze.")
    words = re.findall(r"[a-zA-ZÀ-ÿ]+", text.lower())
    if len(words) >= 10:
        english = sum(word in ENGLISH_WORDS for word in words)
        other = sum(word in OTHER_LANGUAGE_WORDS for word in words)
        if other >= 3 and other > english * 1.5:
            raise UploadError("This document appears to be in another language. Plainclause currently supports English documents only.")
    return text


def parse_upload(filename: str, data: bytes) -> list[Section]:
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise UploadError("File exceeds the 10 MB limit.")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf":
        if not data.startswith(b"%PDF-"):
            raise UploadError("This file is not a valid PDF.")
        if re.search(rb"/(?:JS|JavaScript|OpenAction|AA|Launch|EmbeddedFile)\b", data):
            raise UploadError("This PDF contains active content or attachments. Save a flattened copy before uploading.")
        try:
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise UploadError("Password-protected PDFs are not supported.")
            if len(reader.pages) > MAX_PAGES:
                raise UploadError("PDF exceeds the 200-page limit.")
            sections = []
            total = 0
            ocr_engine = None
            ocr_document = None
            ocr_pages = 0
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text(extraction_mode="layout") or ""
                was_ocr = False
                if len(re.findall(r"[A-Za-z]", text)) < 12:
                    was_ocr = True
                    ocr_pages += 1
                    if ocr_pages > MAX_OCR_PAGES:
                        raise UploadError("OCR is limited to 50 scanned pages per PDF. Split this document into smaller files.")
                    if ocr_engine is None:
                        import fitz
                        from rapidocr import RapidOCR
                        ocr_engine = RapidOCR()
                        ocr_document = fitz.open(stream=data, filetype="pdf")
                    scanned = ocr_document[number - 1]
                    scale = min(2.0, 1800 / max(scanned.rect.width, scanned.rect.height))
                    image = scanned.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
                    ocr_result = ocr_engine(image)
                    text = "\n".join(ocr_result.txts or ())
                    if len(re.findall(r"[A-Za-z]", text)) < 12:
                        raise UploadError(f"Page {number} has too little readable text after OCR. Try a clearer scan.")
                total += len(text)
                if total > MAX_TEXT_CHARS:
                    raise UploadError("The extracted text is too long.")
                if text.strip():
                    page_sections = split_sections(text, number)
                    sections.extend([Section(s.heading, "OCR transcription; verify names, numbers, and dates against the scan.\n" + s.text, s.page) for s in page_sections] if was_ocr else page_sections)
            if not sections:
                raise UploadError("This PDF contains no readable text.")
            _validate_text(" ".join(s.text for s in sections))
            return sections
        except UploadError:
            raise
        except Exception as exc:
            raise UploadError("This PDF could not be read. It may be damaged or unsupported.") from exc
    if suffix == "docx":
        if not data.startswith(b"PK\x03\x04"):
            raise UploadError("This file is not a valid DOCX.")
        try:
            with ZipFile(BytesIO(data)) as archive:
                if len(archive.infolist()) > 1000:
                    raise UploadError("This DOCX contains too many internal files.")
                if sum(item.file_size for item in archive.infolist()) > MAX_ZIP_UNCOMPRESSED:
                    raise UploadError("The DOCX expands beyond the safety limit.")
                if "word/document.xml" not in archive.namelist():
                    raise UploadError("This DOCX has no document body.")
                if any(item.flag_bits & 1 or "vbaproject.bin" in item.filename.lower() or item.filename.lower().startswith("word/embeddings/") for item in archive.infolist()):
                    raise UploadError("This DOCX contains encrypted or embedded active content. Save a clean copy before uploading.")
            doc = Document(BytesIO(data))
            lines = []
            for block in doc.iter_inner_content():
                if isinstance(block, Table):
                    lines.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
                elif block.text.strip():
                    lines.append(block.text)
            text = "\n".join(lines)
            return split_sections(_validate_text(text))
        except UploadError:
            raise
        except Exception as exc:
            raise UploadError("This DOCX could not be read. It may be damaged or unsupported.") from exc
    if suffix == "txt":
        if b"\x00" in data:
            raise UploadError("This does not appear to be a plain-text file.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UploadError("Text files must use UTF-8 encoding.") from exc
        return split_sections(_validate_text(text))
    raise UploadError("Choose a PDF, DOCX, or UTF-8 TXT file.")


def split_sections(text: str, page: int = 1) -> list[Section]:
    """Group clauses by numbered/uppercase headings, with bounded fallback chunks."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    sections: list[Section] = []
    heading = f"Page {page}" if page > 1 else "Document"
    body: list[str] = []

    def flush() -> None:
        nonlocal body
        if body:
            content = "\n".join(body).strip()
            if content:
                sections.append(Section(heading, content, page))
            body = []

    for line in lines:
        if not line:
            continue
        numbered = NUMBERED_CLAUSE.match(line)
        is_clause_body = bool(numbered and (
            len(numbered.group(2)) > 72 or len(numbered.group(2).split()) > 9
            or OPERATIVE_WORD.search(numbered.group(2)) or line.endswith(('.', ';'))
        ))
        is_heading = (len(line) < 120 and (bool(NUMBERED_HEADING.match(line)) or bool(UPPER_HEADING.fullmatch(line)))
                      and not line.endswith(('.', ';')) and not is_clause_body)
        if is_heading:
            flush()
            heading = line
        else:
            if is_clause_body:
                flush()
                heading = f"Clause {numbered.group(1).rstrip('.)')}"
            for piece in textwrap.wrap(line, width=1600, break_long_words=True, break_on_hyphens=False):
                if sum(len(item) for item in body) + len(piece) > 1800:
                    flush()
                body.append(piece)
    flush()
    if not sections and heading != "Document":
        sections.append(Section(heading, heading, page))
    return sections
