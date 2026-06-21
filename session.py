# Backward-compat re-export. Logic lives in src/session/.
from src.session import (
    save_current_session,
    save_named_session,
    load_session,
    list_sessions,
    has_current_session,
)
