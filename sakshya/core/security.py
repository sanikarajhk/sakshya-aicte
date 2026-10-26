"""
Sakshya Security and Role-Based Access Control (RBAC)
Supports Institution, Scrutiny Officer, and Admin roles.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel
from sakshya.core.models import UserRole


class UserSession(BaseModel):
    user_id: str
    username: str
    role: UserRole
    institution_id: Optional[str] = None
    full_name: str


# Pre-configured demonstration users
DEMO_USERS = {
    "inst_user": UserSession(
        user_id="USR-INST-001",
        username="inst_user",
        role=UserRole.INSTITUTION,
        institution_id="INST-001",
        full_name="Dr. R. K. Sharma (Principal / Registrar)"
    ),
    "officer_user": UserSession(
        user_id="USR-OFF-101",
        username="officer_user",
        role=UserRole.SCRUTINY_OFFICER,
        institution_id=None,
        full_name="P. K. Verma (Senior Scrutiny Officer, AICTE)"
    ),
    "admin_user": UserSession(
        user_id="USR-ADM-999",
        username="admin_user",
        role=UserRole.ADMIN,
        institution_id=None,
        full_name="S. Sundaram (Director - Approval Bureau, AICTE)"
    ),
}


def get_current_user(role_name: str = "scrutiny_officer") -> UserSession:
    """Return user session based on selected role."""
    for user in DEMO_USERS.values():
        if user.role.value == role_name:
            return user
    return DEMO_USERS["officer_user"]


def can_review_application(user: UserSession, application_institution_id: str) -> bool:
    """Check if user has permission to review an application."""
    if user.role in (UserRole.SCRUTINY_OFFICER, UserRole.ADMIN):
        return True
    return user.role == UserRole.INSTITUTION and user.institution_id == application_institution_id


def can_approve_rules(user: UserSession) -> bool:
    """Only Admins can approve rule changes from Circulars."""
    return user.role == UserRole.ADMIN


def can_override_decision(user: UserSession) -> bool:
    """Officers and Admins can override automated decisions."""
    return user.role in (UserRole.SCRUTINY_OFFICER, UserRole.ADMIN)
