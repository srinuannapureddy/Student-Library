from datetime import datetime
from sqlalchemy import func
from app.extensions import db


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    isbn = db.Column(db.String(17), nullable=False, unique=True)
    publisher = db.Column(db.String(255))
    edition = db.Column(db.String(50))
    publication_year = db.Column(db.Integer)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(255))
    is_archived = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("Category", back_populates="books")
    copies = db.relationship("BookCopy", back_populates="book", lazy="dynamic")
    requests = db.relationship("BorrowRequest", back_populates="book", lazy="dynamic")

    # Availability is always computed from real copy rows, never stored.
    def _count(self, status=None):
        from app.models.book_copy import BookCopy
        q = db.session.query(func.count(BookCopy.id)).filter(BookCopy.book_id == self.id)
        if status:
            q = q.filter(BookCopy.status == status)
        return q.scalar() or 0

    @property
    def total_copies(self):
        from app.models.book_copy import COPY_LOST
        return self._count() - self._count(COPY_LOST)

    @property
    def available_copies(self):
        return self._count("available")

    @property
    def issued_copies(self):
        return self._count("issued")

    @property
    def unavailable_copies(self):
        return self._count("maintenance")

    def __repr__(self):
        return f"<Book {self.isbn} {self.title!r}>"
