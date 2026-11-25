from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

ROLE_ADMIN = "admin"
ROLE_LIBRARIAN = "librarian"
ROLE_STUDENT = "student"
ROLES = (ROLE_ADMIN, ROLE_LIBRARIAN, ROLE_STUDENT)

STATUS_ACTIVE = "active"
STATUS_RESTRICTED = "restricted"   # may log in but may not borrow
STATUS_INACTIVE = "inactive"       # may not log in (soft-deactivated)
ACCOUNT_STATUSES = (STATUS_ACTIVE, STATUS_RESTRICTED, STATUS_INACTIVE)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT, index=True)
    phone = db.Column(db.String(20))
    student_id = db.Column(db.String(30), unique=True)
    account_status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("role IN ('admin','librarian','student')", name="ck_users_role"),
        db.CheckConstraint("account_status IN ('active','restricted','inactive')", name="ck_users_status"),
    )

    # Loans/requests/notifications are never cascade-deleted: history is preserved.
    loans = db.relationship("Loan", foreign_keys="Loan.student_id", back_populates="student", lazy="dynamic")
    requests = db.relationship("BorrowRequest", foreign_keys="BorrowRequest.student_id",
                               back_populates="student", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):  # Flask-Login hook
        return self.account_status != STATUS_INACTIVE

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_librarian(self):
        return self.role == ROLE_LIBRARIAN

    @property
    def is_student(self):
        return self.role == ROLE_STUDENT

    @property
    def can_borrow(self):
        return self.is_student and self.account_status == STATUS_ACTIVE

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
