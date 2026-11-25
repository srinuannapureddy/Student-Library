from datetime import datetime
from app.extensions import db

DEFAULT_SETTINGS = {
    "library_name": ("Student Library", "Name displayed across the application"),
    "max_books_per_student": ("3", "Maximum active loans per student"),
    "loan_duration_days": ("14", "Default borrowing duration in days"),
    "fine_per_day": ("5.00", "Fine charged per overdue day"),
    "due_soon_days": ("2", "Send a due-soon reminder this many days before the due date"),
}


class LibrarySetting(db.Model):
    __tablename__ = "library_settings"

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(60), nullable=False, unique=True)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, cast=str):
        row = LibrarySetting.query.filter_by(setting_key=key).first()
        raw = row.setting_value if row else DEFAULT_SETTINGS.get(key, ("", ""))[0]
        try:
            return cast(raw)
        except (TypeError, ValueError):
            return cast(DEFAULT_SETTINGS[key][0])

    @staticmethod
    def set(key, value):
        row = LibrarySetting.query.filter_by(setting_key=key).first()
        if row is None:
            row = LibrarySetting(setting_key=key, description=DEFAULT_SETTINGS.get(key, ("", ""))[1],
                                 setting_value=str(value))
            db.session.add(row)
        else:
            row.setting_value = str(value)
        return row

    @staticmethod
    def seed_defaults():
        for key, (value, desc) in DEFAULT_SETTINGS.items():
            if not LibrarySetting.query.filter_by(setting_key=key).first():
                db.session.add(LibrarySetting(setting_key=key, setting_value=value, description=desc))
        db.session.commit()
