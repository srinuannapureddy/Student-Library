from datetime import datetime
from app.extensions import db

REQ_PENDING = "pending"
REQ_APPROVED = "approved"
REQ_REJECTED = "rejected"
REQ_CANCELLED = "cancelled"
REQUEST_STATUSES = (REQ_PENDING, REQ_APPROVED, REQ_REJECTED, REQ_CANCELLED)


class BorrowRequest(db.Model):
    __tablename__ = "borrow_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="RESTRICT"), nullable=False, index=True)
    request_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default=REQ_PENDING, index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = db.Column(db.DateTime)
    review_note = db.Column(db.String(255))

    __table_args__ = (
        db.CheckConstraint("status IN ('pending','approved','rejected','cancelled')", name="ck_request_status"),
    )

    student = db.relationship("User", foreign_keys=[student_id], back_populates="requests")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    book = db.relationship("Book", back_populates="requests")
    loan = db.relationship("Loan", back_populates="request", uselist=False)
