# Alembic autogenerate'in tabloları görmesi için her model burada import edilir.
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.job import EducationLevel, Job, JobStatus
from app.models.user import User, UserRole

__all__ = ["AuditLog", "Base", "EducationLevel", "Job", "JobStatus", "User", "UserRole"]
