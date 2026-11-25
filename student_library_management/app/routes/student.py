from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils.decorators import student_required
from app.models.loan import Loan, LOAN_ACTIVE
from app.models.borrow_request import BorrowRequest, REQ_PENDING
from app.models.fine import Fine, FINE_UNPAID
from app.models.library_setting import LibrarySetting
from app.services.borrowing_service import create_borrow_request, cancel_borrow_request

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/dashboard")
@student_required
def dashboard():
    active_loans = Loan.query.filter_by(student_id=current_user.id, status=LOAN_ACTIVE)\
                             .order_by(Loan.due_date.asc()).all()
    pending_requests = BorrowRequest.query.filter_by(student_id=current_user.id, status=REQ_PENDING)\
                                          .order_by(BorrowRequest.request_date.desc()).all()
    unpaid_fines = Fine.query.join(Loan).filter(
        Loan.student_id == current_user.id,
        Fine.payment_status == FINE_UNPAID
    ).all()

    total_unpaid = sum(f.amount for f in unpaid_fines)
    max_books = LibrarySetting.get("max_books_per_student", int)

    return render_template(
        "student/dashboard.html",
        active_loans=active_loans,
        pending_requests=pending_requests,
        unpaid_fines=unpaid_fines,
        total_unpaid=total_unpaid,
        max_books=max_books
    )


@bp.route("/loans")
@student_required
def loans():
    all_loans = Loan.query.filter_by(student_id=current_user.id)\
                          .order_by(Loan.issued_at.desc()).all()
    return render_template("student/loans.html", loans=all_loans)


@bp.route("/requests")
@student_required
def requests():
    reqs = BorrowRequest.query.filter_by(student_id=current_user.id)\
                              .order_by(BorrowRequest.request_date.desc()).all()
    return render_template("student/requests.html", requests=reqs)


@bp.route("/request/<int:book_id>", methods=["POST"])
@student_required
def request_book(book_id):
    try:
        create_borrow_request(current_user.id, book_id)
        flash("Borrow request submitted successfully! A librarian will review it shortly.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("student.dashboard"))


@bp.route("/cancel-request/<int:request_id>", methods=["POST"])
@student_required
def cancel_request(request_id):
    try:
        cancel_borrow_request(request_id, current_user.id)
        flash("Borrow request has been cancelled.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("student.requests"))


@bp.route("/fines")
@student_required
def fines():
    fines_list = Fine.query.join(Loan).filter(Loan.student_id == current_user.id)\
                           .order_by(Fine.created_at.desc()).all()
    return render_template("student/fines.html", fines=fines_list)

