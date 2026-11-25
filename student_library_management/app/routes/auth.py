from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User, ROLE_STUDENT, STATUS_ACTIVE
from app.utils.validators import normalize_email, validate_password, clean_phone
from app.utils.helpers import is_safe_next, log_action

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        elif current_user.is_librarian:
            return redirect(url_for("librarian.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email_raw = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        try:
            email = normalize_email(email_raw)
        except ValueError:
            email = email_raw.lower()

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email_raw)

        if not user.is_active:
            flash("Your account has been deactivated. Please contact the administrator.", "danger")
            return render_template("auth/login.html", email=email_raw)

        login_user(user, remember=remember)
        log_action(user.id, "USER_LOGIN", "User", user.id, f"User {user.email} signed in")

        next_page = request.args.get("next")
        if is_safe_next(next_page):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for("admin.dashboard"))
        elif user.is_librarian:
            return redirect(url_for("librarian.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("books.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email_raw = request.form.get("email", "").strip()
        student_id = request.form.get("student_id", "").strip()
        phone_raw = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")

        try:
            email = normalize_email(email_raw)
        except ValueError as exc:
            errors.append(str(exc))
            email = None

        if email and User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        if student_id and User.query.filter_by(student_id=student_id).first():
            errors.append("A student with this ID number is already registered.")

        phone = None
        if phone_raw:
            try:
                phone = clean_phone(phone_raw)
            except ValueError as exc:
                errors.append(str(exc))

        if password != confirm_password:
            errors.append("Passwords do not match.")

        pwd_problems = validate_password(password)
        errors.extend(pwd_problems)

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html", full_name=full_name, email=email_raw,
                                   student_id=student_id, phone=phone_raw)

        user = User(
            full_name=full_name,
            email=email,
            student_id=student_id or None,
            phone=phone,
            role=ROLE_STUDENT,
            account_status=STATUS_ACTIVE
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        log_action(user.id, "USER_REGISTERED", "User", user.id, f"Student {user.email} registered")
        flash("Registration successful! You may now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@bp.route("/logout")
@login_required
def logout():
    log_action(current_user.id, "USER_LOGOUT", "User", current_user.id, "User signed out")
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))

