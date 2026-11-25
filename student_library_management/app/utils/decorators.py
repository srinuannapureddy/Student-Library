from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles):
    """Allow only authenticated users whose role is in `roles`; otherwise 403."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


admin_required = roles_required("admin")
staff_required = roles_required("admin", "librarian")
student_required = roles_required("student")
