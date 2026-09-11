"""Idempotent database seeding: schema, roles, permissions, first admin, demo data."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.core.database import sync_engine as engine
from app.core.permissions import DEFAULT_ADMIN_ROLE, DEFAULT_ROLES
from app.core.security import hash_password
from app.models import (
    Assessment,
    Finding,
    LogEntry,
    PostExEvent,
    Report,
    Role,
    User,
)
from app.models.assessment import AssessmentStatus, Severity
from app.models.post_ex import PostExKind


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def seed_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, cfg in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=cfg["description"], is_system=cfg["is_system"])
            role.set_permissions(cfg["permissions"])
            db.add(role)
        elif role.is_system:
            # keep system roles in sync with the catalog, idempotently:
            # only rewrite permissions when they actually differ, and delete the
            # old rows (flush) before inserting new ones to avoid a UNIQUE clash.
            role.description = cfg["description"]
            if set(role.permissions) != set(cfg["permissions"]):
                role.permission_rows.clear()
                db.flush()
                role.set_permissions(cfg["permissions"])
                db.flush()
        roles[name] = role
    db.commit()
    return roles


def seed_admin(db: Session, roles: dict[str, Role]) -> User:
    admin = db.scalar(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL))
    if admin is None:
        admin = User(
            email=settings.FIRST_ADMIN_EMAIL,
            full_name=settings.FIRST_ADMIN_NAME,
            password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
            role=roles[DEFAULT_ADMIN_ROLE],
        )
        db.add(admin)
        db.commit()
    return admin


def seed_demo_data(db: Session, admin: User) -> None:
    if db.scalar(select(Assessment).limit(1)) is not None:
        return  # demo data already present

    targets = [
        ("Corp Web App", "https://app.example.com", "full"),
        ("Drupal Portal", "192.168.70.129", "full"),
        ("Payments API", "https://api.example.com", "api"),
        ("Staging Jenkins", "10.0.4.12:8080", "infra"),
        ("Marketing Site", "https://www.example.com", "quick"),
    ]
    statuses = [
        AssessmentStatus.COMPLETED,
        AssessmentStatus.RUNNING,
        AssessmentStatus.COMPLETED,
        AssessmentStatus.FAILED,
        AssessmentStatus.QUEUED,
    ]
    now = datetime.now(UTC)
    for i, ((name, target, stype), status) in enumerate(zip(targets, statuses, strict=False)):
        created = now - timedelta(days=i, hours=i * 3)
        a = Assessment(
            name=name,
            target=target,
            scan_type=stype,
            status=status,
            phase={
                AssessmentStatus.COMPLETED: "reporting",
                AssessmentStatus.RUNNING: "exploitation",
                AssessmentStatus.FAILED: "vuln-assessment",
                AssessmentStatus.QUEUED: "queued",
            }.get(status, "queued"),
            progress=100.0
            if status == AssessmentStatus.COMPLETED
            else (62.0 if status == AssessmentStatus.RUNNING else 0.0),
            created_by=admin,
            created_at=created,
            started_at=created + timedelta(minutes=2) if status != AssessmentStatus.QUEUED else None,
            finished_at=created + timedelta(hours=1)
            if status in (AssessmentStatus.COMPLETED, AssessmentStatus.FAILED)
            else None,
            error="Tool server timed out" if status == AssessmentStatus.FAILED else None,
        )
        db.add(a)
        db.flush()

        if status == AssessmentStatus.COMPLETED:
            sample = [
                ("Drupalgeddon2 RCE via Forms API", Severity.CRITICAL, "CVE-2018-7600"),
                ("Exposed installer at /core/install.php", Severity.HIGH, None),
                ("Missing security headers", Severity.MEDIUM, None),
                ("Verbose server banner", Severity.LOW, None),
                ("Directory listing enabled", Severity.MEDIUM, None),
            ]
            for title, sev, cve in random.sample(sample, k=random.randint(2, len(sample))):
                db.add(
                    Finding(
                        assessment_id=a.id,
                        title=title,
                        severity=sev,
                        cve=cve,
                        description="Automatically discovered during the assessment.",
                        recommendation="Patch/upgrade the affected component and restrict access.",
                        evidence="See execution logs for the reproducing request/response.",
                    )
                )
            db.add(
                Report(
                    title=f"{name} — Security Assessment Report",
                    assessment_id=a.id,
                    summary=f"Assessment of {target} completed with findings across multiple severities.",
                    generated_by_id=admin.id,
                )
            )
            for kind, ptitle, detail in [
                (PostExKind.SESSION, "Reverse shell established (www-data)", "php/meterpreter session opened."),
                (PostExKind.PRIVESC, "Escalated to root", "Local kernel exploit succeeded."),
                (PostExKind.CREDENTIAL, "Database credentials harvested", "Extracted from app config."),
            ]:
                db.add(PostExEvent(assessment_id=a.id, kind=kind, title=ptitle, detail=detail, host=target))

        for lvl, msg in [
            ("info", f"Assessment '{name}' created"),
            ("info", "Reconnaissance phase started"),
            ("warn", "WAF detected, throttling requests"),
            ("info", "exploit_research tool queried RAG + Metasploit"),
        ]:
            db.add(LogEntry(level=lvl, source="engine", message=msg, assessment_id=a.id, created_at=created))

    db.commit()


def run() -> None:
    create_schema()
    db = SessionLocal()
    try:
        roles = seed_roles(db)
        admin = seed_admin(db, roles)
        seed_demo_data(db, admin)
        print(f"[OK] Seed complete. Admin: {settings.FIRST_ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
