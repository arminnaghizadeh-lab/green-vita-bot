from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class AdminDashboardPreference(Base, TimestampMixin):
    __tablename__ = "admin_dashboard_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    widgets: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
