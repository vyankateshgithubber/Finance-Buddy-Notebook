# user_context.py
from contextvars import ContextVar

# Thread-safe variable to hold the current user's ID
current_user_id: ContextVar[str] = ContextVar("current_user_id", default=None)

def get_current_user_id():
    """Retrieves the user_id for the current request context."""
    val = current_user_id.get()
    if not val:
        # Fallback for testing or if context isn't set
        return "default_user" 
    return val