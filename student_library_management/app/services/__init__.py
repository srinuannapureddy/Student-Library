from app.services.book_service import (
    get_books_paginated, get_book_by_id, create_book, update_book,
    toggle_archive_book, add_book_copy, update_copy_status
)
from app.services.borrowing_service import (
    create_borrow_request, cancel_borrow_request, approve_borrow_request,
    reject_borrow_request, direct_issue_book, return_loan
)
from app.services.fine_service import assess_loan_fine, pay_fine, waive_fine
from app.services.notification_service import send_notification, mark_read, mark_all_read
from app.services.report_service import get_dashboard_metrics, get_overdue_loans, get_category_breakdown

