from typing import Type

from core.dao import Dao
from apps.users.models import User


class UserDao(Dao):
    @property
    def model_cls(self) -> Type[User]:
        return User
