from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.utils.decorators import staff_required
from app.models.book import Book
from app.models.book_copy import BookCopy, COPY_STATUSES
from app.models.borrow_request import BorrowRequest, REQ_PENDING
from app.models.loan import Loan, LOAN_ACTIVE
from app.services.report_service import get_dashboard_metrics, get_overdue_loans
from app.services.borrowing_service import (
    approve_borrow_request, reject_borrow_request, direct_issue_book, return_loan
)
from app.services.book_service import add_book_copy, update_copy_status, get_book_by_id

bp = Blueprint("librarian", __name__, url_prefix="/librarian")


@bp.route("/dashboard")
@staff_required
def dashboard():
    metrics = get_dashboard_metrics()
    pending_requests = BorrowRequest.query.filter_by(status=REQ_PENDING)\
                                          .order_by(BorrowRequest.request_date.asc()).limit(5).all()
    overdue_loans = get_overdue_loans()[:5]

    return render_template(
        "librarian/dashboard.html",
        metrics=metrics,
        pending_requests=pending_requests,
        overdue_loans=overdue_loans
    )


@bp.route("/requests")
@staff_required
def requests():
    status_filter = request.args.get("status", REQ_PENDING)
    query = BorrowRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    reqs = query.order_by(BorrowRequest.request_date.desc()).all()

    return render_template("librarian/requests.html", requests=reqs, current_status=status_filter)


@bp.route("/approve-request/<int:request_id>", methods=["POST"])
@staff_required
def approve_request(request_id):
    copy_id = request.form.get("copy_id", type=int)
    note = request.form.get("note", "").strip() or None
    try:
        approve_borrow_request(request_id, current_user.id, copy_id=copy_id, note=note)
        flash("Borrow request approved and book issued successfully!", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("librarian.requests"))


@bp.route("/reject-request/<int:request_id>", methods=["POST"])
@staff_required
def reject_request(request_id):
    reason = request.form.get("reason", "").strip() or None
    try:
        reject_borrow_request(request_id, current_user.id, reason=reason)
        flash("Borrow request declined.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("librarian.requests"))


@bp.route("/issue", methods=["GET", "POST"])
@staff_required
def issue_book():
    if request.method == "POST":
        accession_number = request.form.get("accession_number", "").strip()
        student_id = request.form.get("student_identifier", "").strip()
        try:
            loan = direct_issue_book(accession_number, student_id, current_user.id)
            flash(f"Book '{loan.book_copy.book.title}' (Copy {accession_number}) issued to {loan.student.full_name}!", "success")
            return redirect(url_for("librarian.loans"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("librarian/issue.html")


@bp.route("/return", methods=["GET", "POST"])
@staff_required
def return_book():
    if request.method == "POST":
        accession_number = request.form.get("accession_number", "").strip()
        copy = BookCopy.query.filter_by(accession_number=accession_number).first()
        if not copy:
            flash(f"No copy found with accession number '{accession_number}'.", "danger")
            return render_template("librarian/return.html")

        active_loan = Loan.query.filter_by(book_copy_id=copy.id, status=LOAN_ACTIVE).first()
        if not active_loan:
            flash(f"Copy {accession_number} is currently marked as '{copy.status}' and has no active loan.", "warning")
            return render_template("librarian/return.html")

        loan, fine = return_loan(active_loan.id, current_user.id)
        msg = f"Book '{loan.book_copy.book.title}' successfully returned from {loan.student.full_name}."
        if fine:
            msg += f" Note: ${fine.amount:.2f} overdue fine assessed ({fine.days_overdue} days)."
        flash(msg, "success" if not fine else "warning")
        return redirect(url_for("librarian.loans"))

    return render_template("librarian/return.html")


@bp.route("/return-loan/<int:loan_id>", methods=["POST"])
@staff_required
def return_loan_action(loan_id):
    try:
        loan, fine = return_loan(loan_id, current_user.id)
        msg = f"Returned '{loan.book_copy.book.title}' from {loan.student.full_name}."
        if fine:
            msg += f" Overdue fine assessed: ${fine.amount:.2f}."
        flash(msg, "success" if not fine else "warning")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("librarian.loans"))


@bp.route("/loans")
@staff_required
def loans():
    filter_type = request.args.get("filter", "active")
    query = Loan.query
    if filter_type == "active":
        query = query.filter_by(status=LOAN_ACTIVE)
    elif filter_type == "overdue":
        from datetime import datetime
        query = query.filter(Loan.status == LOAN_ACTIVE, Loan.due_date < datetime.utcnow())

    all_loans = query.order_by(Loan.issued_at.desc()).all()
    return render_template("librarian/loans.html", loans=all_loans, current_filter=filter_type)


@bp.route("/copies/<int:book_id>", methods=["GET", "POST"])
@staff_required
def manage_copies(book_id):
    book = get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("books.index"))

    if request.method == "POST":
        accession_number = request.form.get("accession_number", "").strip() or None
        try:
            add_book_copy(book.id, accession_number=accession_number, actor_id=current_user.id)
            flash(f"New copy added for '{book.title}'.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("librarian.manage_copies", book_id=book.id))

    return render_template("librarian/copies.html", book=book, statuses=COPY_STATUSES)


@bp.route("/copy-status/<int:copy_id>", methods=["POST"])
@staff_required
def set_copy_status(copy_id):
    new_status = request.form.get("status")
    try:
        copy = update_copy_status(copy_id, new_status, actor_id=current_user.id)
        flash(f"Copy {copy.accession_number} status updated to {new_status}.", "success")
        return redirect(url_for("librarian.manage_copies", book_id=copy.book_id))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("books.index"))

