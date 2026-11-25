from datetime import datetime
from app.extensions import db

LOAN_ACTIVE = "active"
LOAN_RETURNED = "returned"
LOAN_STATUSES = (LOAN_ACTIVE, LOAN_RETURNED)


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    book_copy_id = db.Column(db.Integer, db.ForeignKey("book_copies.id", ondelete="RESTRICT"),
                             nullable=False, index=True)
    request_id = db.Column(db.Integer, db.ForeignKey("borrow_requests.id", ondelete="SET NULL"), unique=True)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    received_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    issued_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    returned_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default=LOAN_ACTIVE, index=True)

    # Equals book_copy_id while the loan is active and NULL once returned.
    # The UNIQUE constraint therefore allows only ONE active loan per physical copy
    # (MySQL permits many NULLs in a unique index), while history stays unlimited.
    active_copy_key = db.Column(db.Integer, unique=True)

    __table_args__ = (
        db.CheckConstraint("status IN ('active','returned')", name="ck_loan_status"),
    )

    student = db.relationship("User", foreign_keys=[student_id], back_populates="loans")
    issuer = db.relationship("User", foreign_keys=[issued_by])
    receiver = db.relationship("User", foreign_keys=[received_by])
    book_copy = db.relationship("BookCopy", back_populates="loans")
    request = db.relationship("BorrowRequest", back_populates="loan")
    fine = db.relationship("Fine", back_populates="loan", uselist=False)

    @property
    def is_overdue(self):
        end = self.returned_at or datetime.utcnow()
        return end > self.due_date

    @property
    def days_overdue(self):
        end = self.returned_at or datetime.utcnow()
        if end <= self.due_date:
            return 0
        return (end.date() - self.due_date.date()).days
