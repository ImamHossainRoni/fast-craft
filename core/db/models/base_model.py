import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from core.db import Base

"""
Module: base_model.py
Author: Imam Hossain Roni

Description: Abstract base model providing a UUID primary key, soft-delete
fields, and created/updated/deleted audit trail (who + when) for every model.
"""


class BaseDBModel(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    inactive: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[uuid.UUID]]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @declared_attr
    def updated_by_id(cls) -> Mapped[Optional[uuid.UUID]]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def deleted_by_id(cls) -> Mapped[Optional[uuid.UUID]]:
        return mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
