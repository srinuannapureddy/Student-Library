import re
from email_validator import validate_email, EmailNotValidError

ISBN_CLEAN = re.compile(r"[\s-]")


def normalize_email(value):
    """Return a normalized email or raise ValueError."""
    try:
        return validate_email((value or "").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(str(exc))


def validate_password(password):
    """Return a list of problems (empty list = acceptable)."""
    problems = []
    if len(password or "") < 8:
        problems.append("Password must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", password or ""):
        problems.append("Password must contain a letter.")
    if not re.search(r"\d", password or ""):
        problems.append("Password must contain a digit.")
    return problems


def normalize_isbn(value):
    """Strip separators; accept valid ISBN-10 or ISBN-13, else raise ValueError."""
    isbn = ISBN_CLEAN.sub("", (value or "")).upper()
    if len(isbn) == 10 and re.fullmatch(r"\d{9}[\dX]", isbn):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(isbn))
        if total % 11 == 0:
            return isbn
    elif len(isbn) == 13 and isbn.isdigit():
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn))
        if total % 10 == 0:
            return isbn
    raise ValueError("Enter a valid ISBN-10 or ISBN-13.")


def validate_year(value, minimum=1000, maximum=None):
    from datetime import date
    maximum = maximum or date.today().year + 1
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValueError("Publication year must be a number.")
    if not minimum <= year <= maximum:
        raise ValueError(f"Publication year must be between {minimum} and {maximum}.")
    return year


def clean_phone(value):
    if not value:
        return None
    phone = re.sub(r"[^\d+]", "", value)
    if not re.fullmatch(r"\+?\d{7,15}", phone):
        raise ValueError("Enter a valid phone number.")
    return phone
