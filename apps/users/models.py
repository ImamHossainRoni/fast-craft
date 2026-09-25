from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.models import BaseDBModel


class User(BaseDBModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
