from datetime import datetime
from app.extensions import db
from app.models.notification import Notification


def send_notification(user_id, title, message, notification_type="info"):
    """Create a new notification for a specific user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def mark_read(notification_id, user_id):
    """Mark a notification as read if it belongs to user."""
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_read(user_id):
    """Mark all notifications as read for user."""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()

