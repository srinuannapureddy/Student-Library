from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.utils.decorators import staff_required
from app.models.fine import Fine, FINE_UNPAID, FINE_PAID, FINE_WAIVED
from app.services.report_service import get_overdue_loans
from app.services.fine_service import pay_fine, waive_fine

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/overdue")
@staff_required
def overdue():
    overdue_loans = get_overdue_loans()
    return render_template("reports/overdue.html", loans=overdue_loans)


@bp.route("/fines")
@staff_required
def fines():
    status_filter = request.args.get("status")
    query = Fine.query
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    fines_list = query.order_by(Fine.created_at.desc()).all()

    return render_template("reports/fines.html", fines=fines_list, current_status=status_filter)


@bp.route("/fines/<int:fine_id>/pay", methods=["POST"])
@staff_required
def process_fine_payment(fine_id):
    try:
        fine = pay_fine(fine_id, current_user.id)
        flash(f"Payment of ${fine.amount:.2f} for loan #{fine.loan_id} recorded.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("reports.fines"))


@bp.route("/fines/<int:fine_id>/waive", methods=["POST"])
@staff_required
def process_fine_waiver(fine_id):
    reason = request.form.get("reason", "").strip() or None
    try:
        fine = waive_fine(fine_id, current_user.id, reason=reason)
        flash(f"Fine #{fine.id} of ${fine.amount:.2f} has been waived.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("reports.fines"))

