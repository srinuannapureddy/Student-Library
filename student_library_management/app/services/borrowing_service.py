from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User, STATUS_ACTIVE
from app.models.book import Book
from app.models.book_copy import BookCopy, COPY_AVAILABLE, COPY_ISSUED
from app.models.borrow_request import (
    BorrowRequest, REQ_PENDING, REQ_APPROVED, REQ_REJECTED, REQ_CANCELLED
)
from app.models.loan import Loan, LOAN_ACTIVE, LOAN_RETURNED
from app.models.library_setting import LibrarySetting
from app.utils.helpers import log_action
from app.services.notification_service import send_notification
from app.services.fine_service import assess_loan_fine


def create_borrow_request(student_id, book_id):
    """Student submits a request to borrow a book."""
    student = User.query.get(student_id)
    if not student or not student.is_student:
        raise ValueError("Only registered students may request books.")

    if not student.can_borrow:
        raise ValueError("Your account is restricted or inactive. You cannot borrow books at this time.")

    book = Book.query.get(book_id)
    if not book or book.is_archived:
        raise ValueError("The requested book is unavailable.")

    # Check student loan limit
    max_books = LibrarySetting.get("max_books_per_student", int)
    active_loans_count = Loan.query.filter_by(student_id=student.id, status=LOAN_ACTIVE).count()
    pending_reqs_count = BorrowRequest.query.filter_by(student_id=student.id, status=REQ_PENDING).count()
    if active_loans_count + pending_reqs_count >= max_books:
        raise ValueError(f"Borrowing limit reached ({max_books} books maximum between active loans and pending requests).")

    # Check for existing active loan or pending request for this specific book
    existing_loan = Loan.query.join(BookCopy).filter(
        Loan.student_id == student.id,
        Loan.status == LOAN_ACTIVE,
        BookCopy.book_id == book.id
    ).first()
    if existing_loan:
        raise ValueError("You currently have an active loan for this book.")

    existing_req = BorrowRequest.query.filter_by(
        student_id=student.id, book_id=book.id, status=REQ_PENDING
    ).first()
    if existing_req:
        raise ValueError("You already have a pending request for this book.")

    if book.available_copies <= 0:
        raise ValueError("There are currently no available copies of this book.")

    request = BorrowRequest(
        student_id=student.id,
        book_id=book.id,
        status=REQ_PENDING,
        request_date=datetime.utcnow()
    )
    db.session.add(request)
    db.session.flush()

    log_action(student.id, "REQUEST_CREATED", "BorrowRequest", request.id,
               f"Requested book '{book.title}'")

    db.session.commit()
    return request


def cancel_borrow_request(request_id, student_id):
    """Cancel a pending request by student."""
    req = BorrowRequest.query.filter_by(id=request_id, student_id=student_id).first()
    if not req:
        raise ValueError("Request not found.")
    if req.status != REQ_PENDING:
        raise ValueError("Only pending requests can be cancelled.")

    req.status = REQ_CANCELLED
    log_action(student_id, "REQUEST_CANCELLED", "BorrowRequest", req.id, "Student cancelled borrow request")
    db.session.commit()
    return req


def approve_borrow_request(request_id, reviewer_id, copy_id=None, note=None):
    """Librarian approves a request and issues a copy."""
    req = BorrowRequest.query.get(request_id)
    if not req:
        raise ValueError("Request not found.")
    if req.status != REQ_PENDING:
        raise ValueError("Request is not pending.")

    # Find an available copy
    if copy_id:
        copy = BookCopy.query.filter_by(id=copy_id, book_id=req.book_id, status=COPY_AVAILABLE).first()
        if not copy:
            raise ValueError("The selected copy is not available.")
    else:
        copy = BookCopy.query.filter_by(book_id=req.book_id, status=COPY_AVAILABLE).first()
        if not copy:
            raise ValueError("No available copy for this book to approve request.")

    # Duration
    duration_days = LibrarySetting.get("loan_duration_days", int)
    now = datetime.utcnow()
    due_date = now + timedelta(days=duration_days)

    req.status = REQ_APPROVED
    req.reviewed_by = reviewer_id
    req.reviewed_at = now
    req.review_note = note

    copy.status = COPY_ISSUED

    loan = Loan(
        student_id=req.student_id,
        book_copy_id=copy.id,
        request_id=req.id,
        issued_by=reviewer_id,
        issued_at=now,
        due_date=due_date,
        status=LOAN_ACTIVE,
        active_copy_key=copy.id
    )
    db.session.add(loan)
    db.session.flush()

    log_action(reviewer_id, "REQUEST_APPROVED", "BorrowRequest", req.id,
               f"Approved request #{req.id} and issued copy {copy.accession_number}")

    send_notification(
        req.student_id,
        "Book Request Approved",
        f"Your request for '{req.book.title}' was approved! Accession #{copy.accession_number}. Due date: {due_date.strftime('%d %b %Y')}.",
        notification_type="success"
    )

    db.session.commit()
    return loan


def reject_borrow_request(request_id, reviewer_id, reason=None):
    """Librarian rejects a request."""
    req = BorrowRequest.query.get(request_id)
    if not req:
        raise ValueError("Request not found.")
    if req.status != REQ_PENDING:
        raise ValueError("Request is not pending.")

    req.status = REQ_REJECTED
    req.reviewed_by = reviewer_id
    req.reviewed_at = datetime.utcnow()
    req.review_note = reason or "Request declined by librarian."

    log_action(reviewer_id, "REQUEST_REJECTED", "BorrowRequest", req.id,
               f"Rejected request #{req.id}: {req.review_note}")

    send_notification(
        req.student_id,
        "Book Request Declined",
        f"Your request for '{req.book.title}' was declined: {req.review_note}",
        notification_type="warning"
    )

    db.session.commit()
    return req


def direct_issue_book(accession_number, student_identifier, librarian_id):
    """Walk-in issue by accession number and student email/student_id."""
    copy = BookCopy.query.filter_by(accession_number=accession_number.strip()).first()
    if not copy:
        raise ValueError(f"No copy found with accession number '{accession_number}'.")
    if copy.status != COPY_AVAILABLE:
        raise ValueError(f"Copy {accession_number} is currently {copy.status} and cannot be issued.")

    identifier = student_identifier.strip()
    student = User.query.filter(
        (User.email == identifier) | (User.student_id == identifier)
    ).first()
    if not student:
        raise ValueError(f"No student found matching '{student_identifier}'.")
    if not student.can_borrow:
        raise ValueError(f"Student {student.full_name} is restricted or inactive.")

    max_books = LibrarySetting.get("max_books_per_student", int)
    active_loans_count = Loan.query.filter_by(student_id=student.id, status=LOAN_ACTIVE).count()
    if active_loans_count >= max_books:
        raise ValueError(f"Student has already reached the maximum borrowing limit of {max_books} books.")

    duration_days = LibrarySetting.get("loan_duration_days", int)
    now = datetime.utcnow()
    due_date = now + timedelta(days=duration_days)

    copy.status = COPY_ISSUED

    loan = Loan(
        student_id=student.id,
        book_copy_id=copy.id,
        issued_by=librarian_id,
        issued_at=now,
        due_date=due_date,
        status=LOAN_ACTIVE,
        active_copy_key=copy.id
    )
    db.session.add(loan)
    db.session.flush()

    log_action(librarian_id, "LOAN_DIRECT_ISSUED", "Loan", loan.id,
               f"Direct issued copy {copy.accession_number} ('{copy.book.title}') to {student.email}")

    send_notification(
        student.id,
        "Book Issued",
        f"'{copy.book.title}' (Copy {copy.accession_number}) has been issued to you. Due date: {due_date.strftime('%d %b %Y')}.",
        notification_type="info"
    )

    db.session.commit()
    return loan


def return_loan(loan_id, librarian_id):
    """Process return of an active loan."""
    loan = Loan.query.get(loan_id)
    if not loan:
        raise ValueError("Loan not found.")
    if loan.status != LOAN_ACTIVE:
        raise ValueError("Loan has already been returned.")

    now = datetime.utcnow()
    loan.status = LOAN_RETURNED
    loan.returned_at = now
    loan.received_by = librarian_id
    loan.active_copy_key = None  # Free unique constraint for future loans

    copy = loan.book_copy
    copy.status = COPY_AVAILABLE

    log_action(librarian_id, "LOAN_RETURNED", "Loan", loan.id,
               f"Returned book copy {copy.accession_number}")

    # Check and assess fine if overdue
    fine = assess_loan_fine(loan, actor_id=librarian_id)

    msg = f"Book '{copy.book.title}' (Copy {copy.accession_number}) has been returned."
    if fine:
        msg += f" Overdue by {fine.days_overdue} days. A fine of ${fine.amount:.2f} has been assessed."

    send_notification(
        loan.student_id,
        "Book Returned",
        msg,
        notification_type="warning" if fine else "success"
    )

    db.session.commit()
    return loan, fine

