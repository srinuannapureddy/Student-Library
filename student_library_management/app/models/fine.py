from datetime import datetime
from app.extensions import db

FINE_UNPAID = "unpaid"
FINE_PAID = "paid"
FINE_WAIVED = "waived"
FINE_STATUSES = (FINE_UNPAID, FINE_PAID, FINE_WAIVED)


class Fine(db.Model):
    __tablename__ = "fines"

    id = db.Column(db.Integer, primary_key=True)
    # UNIQUE loan_id => at most one fine record per loan (no duplicates).
    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id", ondelete="RESTRICT"), nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    days_overdue = db.Column(db.Integer, nullable=False, default=0)
    payment_status = db.Column(db.String(20), nullable=False, default=FINE_UNPAID, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        db.CheckConstraint("amount >= 0", name="ck_fine_amount"),
        db.CheckConstraint("payment_status IN ('unpaid','paid','waived')", name="ck_fine_status"),
    )

    loan = db.relationship("Loan", back_populates="fine")
    recorder = db.relationship("User", foreign_keys=[recorded_by])
