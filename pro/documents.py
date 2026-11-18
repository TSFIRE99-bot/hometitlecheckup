"""Checks every uploaded file before it is stored.

Only PDF, JPEG and PNG are accepted, and the file's first bytes must match its extension, so an HTML page or a program
renamed to .pdf is rejected. There is no virus scanner on this hosting: new files stay quarantined until a staff member
releases them, and downloads are always sent as attachments, never displayed inline.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SIGNATURES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
}
ACTIVE_CONTENT = (b"<script", b"<html", b"<!doctype html", b"<svg", b"<?php")


class UploadRejected(ValueError):
    """Raised with a message that can be shown to the person uploading."""


@dataclass
class CheckedFile:
    filename: str
    content_type: str
    data: bytes
    sha256: str

    @property
    def is_pdf(self) -> bool:
        return self.content_type == "application/pdf"


def safe_filename(name: str) -> str:
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:120] or "upload"


def check_upload(filename: str, data: bytes, max_bytes: int) -> CheckedFile:
    if not data:
        raise UploadRejected("The file is empty.")
    if len(data) > max_bytes:
        raise UploadRejected(f"The file is larger than {max_bytes // (1024 * 1024)} MB. Try a smaller scan or photo.")
    name = safe_filename(filename)
    extension = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if extension not in SIGNATURES:
        raise UploadRejected("Only PDF, JPG and PNG files can be uploaded.")
    signature, content_type = SIGNATURES[extension]
    if not data.startswith(signature):
        raise UploadRejected("This file isn't really a " + extension[1:].upper() + ". Please upload the original file.")
    head = data[:2048].lower()
    if any(marker in head for marker in ACTIVE_CONTENT):
        raise UploadRejected("This file contains web page code and can't be accepted.")
    if content_type == "application/pdf" and pdf_active_content(data):
        raise UploadRejected("This PDF contains scripts, actions or attached files, which HomeKeep doesn't accept. "
                             "Print it to a new PDF or scan the paper copy, and upload that instead.")
    return CheckedFile(name, content_type, data, hashlib.sha256(data).hexdigest())


# PDF features that run code, open other programs or carry other files. Deeds, certificates and tax bills don't
# need any of them. A best-effort check, not a virus scanner: it reads the raw file (with #xx-escaped names decoded,
# a common way to hide them) and the document structure through pypdf, which also sees compressed object streams.
PDF_DANGEROUS = (b"/javascript", b"/js", b"/launch", b"/embeddedfile", b"/embeddedfiles", b"/richmedia",
                 b"/submitform", b"/importdata", b"/xfa")
_PDF_NAME = re.compile(rb"/[A-Za-z0-9#_.+-]+")


_PDF_STREAM = re.compile(rb"stream\r?\n.*?endstream", re.S)


def _decoded_names(data: bytes) -> set[bytes]:
    # Stream contents are skipped: compressed image bytes can spell "/JS" by chance, and a scan must not be refused
    # for that. Names hidden inside compressed object streams are found by _structure_names instead.
    names = set()
    for match in _PDF_NAME.finditer(_PDF_STREAM.sub(b"", data)):
        raw = match.group()
        if b"#" in raw:
            raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
        names.add(raw.lower())
    return names


def _structure_names(data: bytes) -> set[bytes]:
    """Every dictionary key and name value pypdf can reach from the document root, including compressed objects."""
    try:
        import io

        from pypdf import PdfReader
        from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject
        reader = PdfReader(io.BytesIO(data))
        found: set[bytes] = set()
        seen: set[int] = set()
        stack = [reader.trailer]
        while stack and len(seen) < 20000:
            item = stack.pop()
            if isinstance(item, IndirectObject):
                key = (item.idnum, item.generation)
                if key in seen:
                    continue
                seen.add(key)
                item = item.get_object()
            if isinstance(item, DictionaryObject):
                for k, v in item.items():
                    found.add(str(k).lower().encode())
                    stack.append(v)
            elif isinstance(item, ArrayObject):
                stack.extend(item)
            elif isinstance(item, NameObject):
                found.add(str(item).lower().encode())
        return found
    except Exception:                       # unreadable structure: the raw scan still applies, and reading flags it
        return set()


def pdf_active_content(data: bytes) -> bool:
    names = _decoded_names(data) | _structure_names(data)
    return any(name in names for name in PDF_DANGEROUS)
