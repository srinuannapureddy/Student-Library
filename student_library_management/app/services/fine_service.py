from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models.fine import Fine, FINE_UNPAID, FINE_PAID, FINE_WAIVED
from app.models.library_setting import LibrarySetting
from app.utils.helpers import log_action
from app.services.notification_service import send_notification


def assess_loan_fine(loan, actor_id=None):
    """Assess or update the fine for an overdue loan."""
    if not loan.is_overdue:
        return None

    days = loan.days_overdue
    if days <= 0:
        return None

    daily_rate = Decimal(LibrarySetting.get("fine_per_day", str))
    fine_amount = round(Decimal(days) * daily_rate, 2)

    fine = Fine.query.filter_by(loan_id=loan.id).first()
    if fine:
        if fine.payment_status == FINE_UNPAID:
            fine.days_overdue = days
            fine.amount = fine_amount
    else:
        fine = Fine(
            loan_id=loan.id,
            amount=fine_amount,
            days_overdue=days,
            payment_status=FINE_UNPAID,
            created_at=datetime.utcnow()
        )
        db.session.add(fine)

    db.session.commit()
    return fine


def pay_fine(fine_id, actor_id):
    """Mark a fine as paid."""
    fine = Fine.query.get(fine_id)
    if not fine:
        raise ValueError("Fine record not found.")
    if fine.payment_status != FINE_UNPAID:
        raise ValueError("Fine is already settled.")

    fine.payment_status = FINE_PAID
    fine.paid_at = datetime.utcnow()
    fine.recorded_by = actor_id
    log_action(actor_id, "FINE_PAID", "Fine", fine.id, f"Collected fine of {fine.amount} for loan {fine.loan_id}")

    # Notify student
    student_id = fine.loan.student_id
    send_notification(
        student_id,
        "Fine Payment Received",
        f"Your fine payment of ${fine.amount:.2f} for loan #{fine.loan_id} has been recorded.",
        notification_type="success"
    )
    db.session.commit()
    return fine


def waive_fine(fine_id, actor_id, reason=None):
    """Waive a fine."""
    fine = Fine.query.get(fine_id)
    if not fine:
        raise ValueError("Fine record not found.")
    if fine.payment_status != FINE_UNPAID:
        raise ValueError("Fine is already settled.")

    fine.payment_status = FINE_WAIVED
    fine.paid_at = datetime.utcnow()
    fine.recorded_by = actor_id
    desc = f"Waived fine of {fine.amount} for loan {fine.loan_id}. Reason: {reason or 'Administrative discretion'}"
    log_action(actor_id, "FINE_WAIVED", "Fine", fine.id, desc)

    student_id = fine.loan.student_id
    send_notification(
        student_id,
        "Fine Waived",
        f"Your fine of ${fine.amount:.2f} for loan #{fine.loan_id} has been waived.",
        notification_type="info"
    )
    db.session.commit()
    return fine

