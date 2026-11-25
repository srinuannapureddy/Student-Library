from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app.models.notification import Notification
from app.services.notification_service import mark_read, mark_all_read

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.route("/")
@login_required
def index():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.created_at.desc()).all()
    return render_template("notifications/index.html", notifications=notifs)


@bp.route("/read/<int:notif_id>", methods=["POST"])
@login_required
def read(notif_id):
    mark_read(notif_id, current_user.id)
    return redirect(request.referrer or url_for("notifications.index"))


@bp.route("/read-all", methods=["POST"])
@login_required
def read_all():
    mark_all_read(current_user.id)
    return redirect(request.referrer or url_for("notifications.index"))

