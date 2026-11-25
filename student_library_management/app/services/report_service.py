from datetime import datetime
from sqlalchemy import func
from app.extensions import db
from app.models.book import Book
from app.models.book_copy import BookCopy, COPY_AVAILABLE, COPY_ISSUED, COPY_MAINTENANCE, COPY_LOST
from app.models.borrow_request import BorrowRequest, REQ_PENDING
from app.models.loan import Loan, LOAN_ACTIVE
from app.models.fine import Fine, FINE_UNPAID
from app.models.user import User, ROLE_STUDENT
from app.models.category import Category


def get_dashboard_metrics():
    """Retrieve high-level metrics for admin and librarian dashboards."""
    total_books = Book.query.filter_by(is_archived=False).count()
    total_copies = BookCopy.query.count()
    available_copies = BookCopy.query.filter_by(status=COPY_AVAILABLE).count()
    issued_copies = BookCopy.query.filter_by(status=COPY_ISSUED).count()

    active_loans = Loan.query.filter_by(status=LOAN_ACTIVE).count()
    now = datetime.utcnow()
    overdue_loans = Loan.query.filter(Loan.status == LOAN_ACTIVE, Loan.due_date < now).count()

    pending_requests = BorrowRequest.query.filter_by(status=REQ_PENDING).count()
    total_students = User.query.filter_by(role=ROLE_STUDENT).count()

    unpaid_fines_sum = db.session.query(func.coalesce(func.sum(Fine.amount), 0)).filter(
        Fine.payment_status == FINE_UNPAID
    ).scalar() or 0

    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "issued_copies": issued_copies,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "pending_requests": pending_requests,
        "total_students": total_students,
        "unpaid_fines_sum": float(unpaid_fines_sum)
    }


def get_overdue_loans():
    """Return all currently active overdue loans ordered by days overdue."""
    now = datetime.utcnow()
    return Loan.query.filter(
        Loan.status == LOAN_ACTIVE,
        Loan.due_date < now
    ).order_by(Loan.due_date.asc()).all()


def get_category_breakdown():
    """Count of books per category for analytics."""
    rows = db.session.query(
        Category.category_name,
        func.count(Book.id)
    ).outerjoin(Book, (Category.id == Book.category_id) & (Book.is_archived == False))\
     .group_by(Category.category_name)\
     .all()
    return [{"category": r[0], "count": r[1]} for r in rows]

