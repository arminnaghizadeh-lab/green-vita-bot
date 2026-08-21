import enum


class VisitStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
