from app.extensions import db
from app.models.book import Book
from app.models.book_copy import BookCopy, COPY_AVAILABLE, COPY_STATUSES
from app.models.category import Category
from app.utils.helpers import save_cover_image, delete_cover_image, log_action
from app.utils.validators import normalize_isbn, validate_year


def get_books_paginated(search=None, category_id=None, page=1, per_page=12, include_archived=False):
    """Query books with search and category filters."""
    query = Book.query
    if not include_archived:
        query = query.filter_by(is_archived=False)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Book.title.ilike(term)) |
            (Book.author.ilike(term)) |
            (Book.isbn.ilike(term)) |
            (Book.publisher.ilike(term))
        )

    return query.order_by(Book.title.asc()).paginate(page=page, per_page=per_page, error_out=False)


def get_book_by_id(book_id):
    """Retrieve book by id or None."""
    return Book.query.get(book_id)


def create_book(data, cover_file=None, actor_id=None):
    """Validate and create a new book with optional initial copies."""
    isbn = normalize_isbn(data.get("isbn"))
    if Book.query.filter_by(isbn=isbn).first():
        raise ValueError(f"A book with ISBN {isbn} already exists.")

    year = data.get("publication_year")
    if year:
        year = validate_year(year)

    cover_filename = None
    if cover_file:
        cover_filename = save_cover_image(cover_file)

    book = Book(
        title=data["title"].strip(),
        author=data["author"].strip(),
        isbn=isbn,
        publisher=data.get("publisher", "").strip() or None,
        edition=data.get("edition", "").strip() or None,
        publication_year=year,
        category_id=data.get("category_id") or None,
        description=data.get("description", "").strip() or None,
        cover_image=cover_filename,
    )
    db.session.add(book)
    db.session.flush()

    # Optional initial copies count
    initial_copies = int(data.get("initial_copies", 0) or 0)
    for i in range(1, initial_copies + 1):
        acc = f"{isbn[:5]}-{book.id:04d}-{i:03d}"
        copy = BookCopy(book_id=book.id, accession_number=acc, status=COPY_AVAILABLE)
        db.session.add(copy)

    if actor_id:
        log_action(actor_id, "BOOK_CREATED", "Book", book.id, f"Created book '{book.title}' with {initial_copies} copies")

    db.session.commit()
    return book


def update_book(book_id, data, cover_file=None, actor_id=None):
    """Update book details."""
    book = Book.query.get(book_id)
    if not book:
        raise ValueError("Book not found.")

    isbn = normalize_isbn(data.get("isbn"))
    existing = Book.query.filter_by(isbn=isbn).first()
    if existing and existing.id != book.id:
        raise ValueError(f"Another book already has ISBN {isbn}.")

    year = data.get("publication_year")
    if year:
        year = validate_year(year)

    book.title = data["title"].strip()
    book.author = data["author"].strip()
    book.isbn = isbn
    book.publisher = data.get("publisher", "").strip() or None
    book.edition = data.get("edition", "").strip() or None
    book.publication_year = year
    book.category_id = data.get("category_id") or None
    book.description = data.get("description", "").strip() or None

    if cover_file and cover_file.filename:
        old_cover = book.cover_image
        book.cover_image = save_cover_image(cover_file)
        if old_cover:
            delete_cover_image(old_cover)

    if actor_id:
        log_action(actor_id, "BOOK_UPDATED", "Book", book.id, f"Updated book '{book.title}'")

    db.session.commit()
    return book


def toggle_archive_book(book_id, actor_id=None):
    """Toggle archived state for a book."""
    book = Book.query.get(book_id)
    if not book:
        raise ValueError("Book not found.")

    book.is_archived = not book.is_archived
    status_str = "Archived" if book.is_archived else "Unarchived"
    if actor_id:
        log_action(actor_id, "BOOK_ARCHIVED" if book.is_archived else "BOOK_UNARCHIVED",
                   "Book", book.id, f"{status_str} book '{book.title}'")

    db.session.commit()
    return book


def add_book_copy(book_id, accession_number=None, actor_id=None):
    """Add a new physical copy for a book."""
    book = Book.query.get(book_id)
    if not book:
        raise ValueError("Book not found.")

    if not accession_number:
        count = book.copies.count() + 1
        accession_number = f"{book.isbn[:5]}-{book.id:04d}-{count:03d}"

    if BookCopy.query.filter_by(accession_number=accession_number).first():
        raise ValueError(f"Accession number '{accession_number}' already exists.")

    copy = BookCopy(book_id=book.id, accession_number=accession_number, status=COPY_AVAILABLE)
    db.session.add(copy)
    db.session.flush()

    if actor_id:
        log_action(actor_id, "COPY_ADDED", "BookCopy", copy.id,
                   f"Added copy {accession_number} to '{book.title}'")

    db.session.commit()
    return copy


def update_copy_status(copy_id, new_status, actor_id=None):
    """Update status of a book copy."""
    copy = BookCopy.query.get(copy_id)
    if not copy:
        raise ValueError("Book copy not found.")
    if new_status not in COPY_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    old_status = copy.status
    copy.status = new_status
    if actor_id:
        log_action(actor_id, "COPY_STATUS_CHANGED", "BookCopy", copy.id,
                   f"Changed copy {copy.accession_number} status from {old_status} to {new_status}")

    db.session.commit()
    return copy

