import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Direction(str, enum.Enum):
    ABOVE = "above"
    BELOW = "below"


class AlertORM(Base):
    __tablename__ = "alerts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str]
    target_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    direction: Mapped[Direction]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))