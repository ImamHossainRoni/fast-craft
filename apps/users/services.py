from typing import Type

from apps.users.dao import UserDao
from apps.users.schemas import UserCreationSchema
from core.dao import Dao
from core.security import hash_password
from core.service import ReadService, WriteService


class UserReadService(ReadService):
    @property
    def dao_cls(self) -> Type[Dao]:
        return UserDao


class UserWriteService(WriteService):
    @property
    def dao_cls(self) -> Type[Dao]:
        return UserDao

    async def register(self, data: UserCreationSchema, commit: bool = True):
        """Create a new user with its password hashed before it ever reaches the DAO."""
        payload = data.model_dump()
        payload["password"] = hash_password(payload["password"])
        return await self.create(payload, commit=commit)
