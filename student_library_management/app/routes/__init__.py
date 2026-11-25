from app.routes.auth import bp as auth_bp
from app.routes.books import bp as books_bp
from app.routes.student import bp as student_bp
from app.routes.librarian import bp as librarian_bp
from app.routes.admin import bp as admin_bp
from app.routes.reports import bp as reports_bp
from app.routes.notifications import bp as notifications_bp

__all__ = [
    "auth_bp",
    "books_bp",
    "student_bp",
    "librarian_bp",
    "admin_bp",
    "reports_bp",
    "notifications_bp",
]

