from datetime import datetime
from app.extensions import db

COPY_AVAILABLE = "available"
COPY_ISSUED = "issued"
COPY_MAINTENANCE = "maintenance"
COPY_LOST = "lost"
COPY_STATUSES = (COPY_AVAILABLE, COPY_ISSUED, COPY_MAINTENANCE, COPY_LOST)


class BookCopy(db.Model):
    __tablename__ = "book_copies"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="RESTRICT"), nullable=False, index=True)
    accession_number = db.Column(db.String(50), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default=COPY_AVAILABLE, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("status IN ('available','issued','maintenance','lost')", name="ck_copy_status"),
    )

    book = db.relationship("Book", back_populates="copies")
    loans = db.relationship("Loan", back_populates="book_copy", lazy="dynamic")

    def __repr__(self):
        return f"<BookCopy {self.accession_number} {self.status}>"
