import os
import uuid
from datetime import datetime
from decimal import Decimal
from flask import current_app, request, url_for
from werkzeug.utils import secure_filename
from app.extensions import db

# Magic-number signatures used to verify uploaded images by content, not just extension.
_SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
}


def log_action(user_id, action, entity_type, entity_id=None, description=None):
    """Add an audit-log row to the CURRENT session (caller commits)."""
    from app.models.audit_log import AuditLog
    db.session.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type,
                            entity_id=entity_id, description=(description or "")[:500]))


def save_cover_image(file_storage):
    """Validate and store an uploaded cover image. Returns the stored filename or None.
    Raises ValueError for invalid uploads."""
    if not file_storage or not file_storage.filename:
        return None
    name = secure_filename(file_storage.filename)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise ValueError("Cover image must be a PNG, JPG or WEBP file.")
    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in _SIGNATURES[ext]) or (ext == "webp" and b"WEBP" not in head):
        raise ValueError("The uploaded file is not a valid image.")
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, stored))
    return stored


def delete_cover_image(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    try:
        os.remove(path)
    except OSError:
        pass


def cover_url(filename):
    return url_for("static", filename=f"uploads/{filename}") if filename else None


def money(value):
    return f"{Decimal(value or 0):,.2f}"


def fmt_dt(value, with_time=False):
    if not value:
        return "—"
    return value.strftime("%d %b %Y, %H:%M") if with_time else value.strftime("%d %b %Y")


def is_safe_next(target):
    """Only allow same-site relative redirects after login."""
    return bool(target) and target.startswith("/") and not target.startswith("//")
