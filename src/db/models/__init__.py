"""
همه مدل‌ها اینجا import می‌شوند تا Alembic هنگام autogenerate
همه‌ی جدول‌ها را از طریق Base.metadata ببیند.
"""

from src.db.models.conversation import Conversation, MessageRole
from src.db.models.diagnosis import Diagnosis, DiagnosisSeverity
from src.db.models.plant import Plant, PlantHealthStatus
from src.db.models.plant_identification import DifficultyLevel, PlantIdentification
from src.db.models.reminder import Reminder, ReminderType
from src.db.models.user import User
from src.db.models.visit_status import VisitStatus
from src.db.models.visit_appointment import AppointmentStatus, VisitAppointment
from src.db.models.smart_bio_click import SmartBioClick

__all__ = [
    "User",
    "Plant",
    "PlantHealthStatus",
    "Conversation",
    "MessageRole",
    "Reminder",
    "ReminderType",
    "Diagnosis",
    "DiagnosisSeverity",
    "PlantIdentification",
    "DifficultyLevel",
    "VisitStatus",
    "VisitAppointment",
    "AppointmentStatus",
    "SmartBioClick",
]

from src.db.models.push_subscription import PushSubscription
