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
from src.db.models.web_account import (
    WebAccount,
    WebDiagnosisUsage,
    WebPasswordResetToken,
)

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

from src.db.models.booking import (
    Booking,
    BookingSchedule,
    BookingSlotAssignment,
    BookingSource,
    BookingStatus,
    BookingTimeSlot,
    Service,
)

__all__ += [
    "Service",
    "BookingSchedule",
    "BookingTimeSlot",
    "BookingSlotAssignment",
    "Booking",
    "BookingSource",
    "BookingStatus",
    "WebAccount",
    "WebDiagnosisUsage",
    "WebPasswordResetToken",
]

from src.db.models.accounting import (
    AccountingAccount,
    AccountingJournal,
    AccountingJournalLine,
)

__all__ += [
    "AccountingAccount",
    "AccountingJournal",
    "AccountingJournalLine",
]

from src.db.models.inventory import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryMovement,
    InventoryWarehouse,
)

__all__ += [
    "InventoryDocument",
    "InventoryDocumentLine",
    "InventoryMovement",
    "InventoryWarehouse",
]
from src.db.models.admin_dashboard_preference import AdminDashboardPreference
__all__ += ["AdminDashboardPreference"]
