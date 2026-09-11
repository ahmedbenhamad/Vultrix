"""Central permission catalog and default role definitions for RBAC.

Permissions are simple ``resource:action`` strings. Roles are collections of
permissions. The seed script materializes these into the database; the catalog
here is the single source of truth so the UI and API stay in sync.
"""

from enum import StrEnum


class Permission(StrEnum):
    # Dashboard / stats
    STATS_READ = "stats:read"

    # Assessments (the core Strix scans)
    ASSESSMENT_READ = "assessment:read"
    ASSESSMENT_READ_ALL = "assessment:read:all"  # see others' assessments, not just own
    ASSESSMENT_CREATE = "assessment:create"
    ASSESSMENT_RUN = "assessment:run"
    ASSESSMENT_CANCEL = "assessment:cancel"
    ASSESSMENT_DELETE = "assessment:delete"

    # Findings triage
    FINDING_TRIAGE = "finding:triage"

    # Scheduled scans
    SCHEDULE_READ = "schedule:read"
    SCHEDULE_MANAGE = "schedule:manage"

    # Logs
    LOG_READ = "log:read"

    # Reports
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"

    # AI assistant
    ASSISTANT_USE = "assistant:use"

    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Role / permission management
    ROLE_READ = "role:read"
    ROLE_MANAGE = "role:manage"

    # Audit trail
    AUDIT_READ = "audit:read"

    # System settings
    SETTINGS_MANAGE = "settings:manage"


# Human-friendly descriptions, surfaced in the role-management UI.
PERMISSION_DESCRIPTIONS: dict[str, str] = {
    Permission.STATS_READ: "View dashboard statistics",
    Permission.ASSESSMENT_READ: "View own assessments and their results",
    Permission.ASSESSMENT_READ_ALL: "View all users' assessments (not just own)",
    Permission.ASSESSMENT_CREATE: "Create new assessments",
    Permission.ASSESSMENT_RUN: "Start / launch assessments",
    Permission.ASSESSMENT_CANCEL: "Cancel running assessments",
    Permission.ASSESSMENT_DELETE: "Delete assessments",
    Permission.FINDING_TRIAGE: "Triage findings (status, assignee, severity override)",
    Permission.SCHEDULE_READ: "View scheduled scans",
    Permission.SCHEDULE_MANAGE: "Create / edit / delete scheduled scans",
    Permission.LOG_READ: "View execution logs",
    Permission.REPORT_READ: "View reports",
    Permission.REPORT_EXPORT: "Export reports (CSV / PDF / JSON)",
    Permission.ASSISTANT_USE: "Use the AI assistant",
    Permission.USER_READ: "View users",
    Permission.USER_CREATE: "Create users",
    Permission.USER_UPDATE: "Edit users",
    Permission.USER_DELETE: "Delete users",
    Permission.ROLE_READ: "View roles and permissions",
    Permission.ROLE_MANAGE: "Create / edit roles and assign permissions",
    Permission.AUDIT_READ: "View the audit trail",
    Permission.SETTINGS_MANAGE: "Manage system settings",
}

ALL_PERMISSIONS: list[str] = [str(p) for p in Permission]


# ── Default roles ────────────────────────────────────────────────────────────
# ``is_system`` roles cannot be deleted from the UI.

_VIEWER = [
    Permission.STATS_READ,
    Permission.ASSESSMENT_READ,
    Permission.LOG_READ,
    Permission.REPORT_READ,
]

_ANALYST = _VIEWER + [
    Permission.ASSESSMENT_CREATE,
    Permission.ASSESSMENT_RUN,
    Permission.ASSESSMENT_CANCEL,
    Permission.FINDING_TRIAGE,
    Permission.SCHEDULE_READ,
    Permission.SCHEDULE_MANAGE,
    Permission.REPORT_EXPORT,
    Permission.ASSISTANT_USE,
]

_MANAGER = _ANALYST + [
    Permission.ASSESSMENT_READ_ALL,  # managers oversee everyone's assessments
    Permission.ASSESSMENT_DELETE,
    Permission.USER_READ,
    Permission.AUDIT_READ,
]

DEFAULT_ROLES: dict[str, dict] = {
    "admin": {
        "description": "Full administrative access to everything.",
        "is_system": True,
        "permissions": ALL_PERMISSIONS,
    },
    "manager": {
        "description": "Runs assessments, manages the queue, views users and audit.",
        "is_system": True,
        "permissions": [str(p) for p in _MANAGER],
    },
    "analyst": {
        "description": "Creates and runs assessments, exports reports, uses the assistant.",
        "is_system": True,
        "permissions": [str(p) for p in _ANALYST],
    },
    "viewer": {
        "description": "Read-only access to assessments, logs and reports.",
        "is_system": True,
        "permissions": [str(p) for p in _VIEWER],
    },
}

DEFAULT_ADMIN_ROLE = "admin"
DEFAULT_NEW_USER_ROLE = "viewer"
