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
    return CheckedFile(name, content_type, data, hashlib.sha256(data).hexdigest())
