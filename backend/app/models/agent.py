from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    daily_budget_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("1.0")
    )
    spent_today_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0")
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
