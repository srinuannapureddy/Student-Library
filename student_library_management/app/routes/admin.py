from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.extensions import db
from app.utils.decorators import admin_required
from app.models.user import User, ROLES, ACCOUNT_STATUSES, STATUS_ACTIVE, STATUS_INACTIVE, STATUS_RESTRICTED
from app.models.category import Category
from app.models.book import Book
from app.models.library_setting import LibrarySetting, DEFAULT_SETTINGS
from app.models.audit_log import AuditLog
from app.services.book_service import create_book, update_book, toggle_archive_book, get_book_by_id
from app.services.report_service import get_dashboard_metrics, get_category_breakdown
from app.utils.validators import normalize_email, validate_password
from app.utils.helpers import log_action

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@admin_required
def dashboard():
    metrics = get_dashboard_metrics()
    category_data = get_category_breakdown()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        metrics=metrics,
        category_data=category_data,
        recent_logs=recent_logs,
        recent_users=recent_users
    )


@bp.route("/users")
@admin_required
def users():
    role_filter = request.args.get("role")
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    all_users = query.order_by(User.created_at.desc()).all()

    return render_template("admin/users.html", users=all_users, current_role=role_filter, roles=ROLES)


@bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def create_staff_user():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email_raw = request.form.get("email", "").strip()
        role = request.form.get("role")
        password = request.form.get("password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if role not in ROLES:
            errors.append("Invalid user role selected.")

        try:
            email = normalize_email(email_raw)
        except ValueError as exc:
            errors.append(str(exc))
            email = None

        if email and User.query.filter_by(email=email).first():
            errors.append("A user with this email already exists.")

        pwd_errs = validate_password(password)
        errors.extend(pwd_errs)

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("admin/create_user.html", full_name=full_name, email=email_raw, role=role, roles=ROLES)

        user = User(
            full_name=full_name,
            email=email,
            role=role,
            account_status=STATUS_ACTIVE
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        log_action(current_user.id, "USER_CREATED_BY_ADMIN", "User", user.id,
                   f"Created staff account {user.email} with role {user.role}")
        db.session.commit()

        flash(f"User {user.email} successfully created.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/create_user.html", roles=ROLES)


@bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_required
def update_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot modify your own administrator account status.", "warning")
        return redirect(url_for("admin.users"))

    new_status = request.form.get("status")
    if new_status in ACCOUNT_STATUSES:
        old_status = user.account_status
        user.account_status = new_status
        log_action(current_user.id, "USER_STATUS_CHANGED", "User", user.id,
                   f"Changed {user.email} status from {old_status} to {new_status}")
        db.session.commit()
        flash(f"Status for {user.full_name} updated to {new_status}.", "success")

    return redirect(url_for("admin.users"))


@bp.route("/books")
@admin_required
def books():
    all_books = Book.query.order_by(Book.created_at.desc()).all()
    return render_template("admin/books.html", books=all_books)


@bp.route("/books/create", methods=["GET", "POST"])
@admin_required
def add_book():
    categories = Category.query.order_by(Category.category_name.asc()).all()
    if request.method == "POST":
        data = {
            "title": request.form.get("title", ""),
            "author": request.form.get("author", ""),
            "isbn": request.form.get("isbn", ""),
            "publisher": request.form.get("publisher", ""),
            "edition": request.form.get("edition", ""),
            "publication_year": request.form.get("publication_year", ""),
            "category_id": request.form.get("category_id", type=int),
            "description": request.form.get("description", ""),
            "initial_copies": request.form.get("initial_copies", 1, type=int),
        }
        cover_file = request.files.get("cover_image")
        try:
            book = create_book(data, cover_file=cover_file, actor_id=current_user.id)
            flash(f"Book '{book.title}' added successfully with {data['initial_copies']} copies!", "success")
            return redirect(url_for("admin.books"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("admin/book_form.html", book=None, categories=categories)


@bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    book = get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("admin.books"))

    categories = Category.query.order_by(Category.category_name.asc()).all()
    if request.method == "POST":
        data = {
            "title": request.form.get("title", ""),
            "author": request.form.get("author", ""),
            "isbn": request.form.get("isbn", ""),
            "publisher": request.form.get("publisher", ""),
            "edition": request.form.get("edition", ""),
            "publication_year": request.form.get("publication_year", ""),
            "category_id": request.form.get("category_id", type=int),
            "description": request.form.get("description", ""),
        }
        cover_file = request.files.get("cover_image")
        try:
            update_book(book.id, data, cover_file=cover_file, actor_id=current_user.id)
            flash(f"Book '{book.title}' updated successfully!", "success")
            return redirect(url_for("admin.books"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("admin/book_form.html", book=book, categories=categories)


@bp.route("/books/<int:book_id>/archive", methods=["POST"])
@admin_required
def archive_book(book_id):
    try:
        book = toggle_archive_book(book_id, actor_id=current_user.id)
        msg = f"Book '{book.title}' archived." if book.is_archived else f"Book '{book.title}' unarchived."
        flash(msg, "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.books"))


@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("category_name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Category name cannot be empty.", "danger")
        elif Category.query.filter_by(category_name=name).first():
            flash(f"Category '{name}' already exists.", "warning")
        else:
            cat = Category(category_name=name, description=description or None)
            db.session.add(cat)
            db.session.commit()
            log_action(current_user.id, "CATEGORY_CREATED", "Category", cat.id, f"Added category '{name}'")
            flash(f"Category '{name}' added successfully.", "success")
            return redirect(url_for("admin.categories"))

    cats = Category.query.order_by(Category.category_name.asc()).all()
    return render_template("admin/categories.html", categories=cats)


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS.keys():
            val = request.form.get(key, "").strip()
            if val:
                LibrarySetting.set(key, val)
        db.session.commit()
        log_action(current_user.id, "SETTINGS_UPDATED", "LibrarySetting", None, "Updated library configuration settings")
        flash("Library settings updated successfully.", "success")
        return redirect(url_for("admin.settings"))

    current_settings = {}
    for key, (default_val, desc) in DEFAULT_SETTINGS.items():
        current_settings[key] = {
            "value": LibrarySetting.get(key, str),
            "description": desc
        }

    return render_template("admin/settings.html", settings=current_settings)


@bp.route("/audit-logs")
@admin_required
def audit_logs():
    page = request.args.get("page", 1, type=int)
    logs_pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/audit_logs.html", pagination=logs_pagination, logs=logs_pagination.items)

