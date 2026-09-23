from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dao import Dao, DataInput
from core.db import Base, get_db

"""
Module: base_service.py
Author: Imam Hossain Roni

Description: Abstract base service. Each child service must define dao_cls
(a DAO class). The service owns the AsyncSession (injected once via FastAPI's
Depends(get_db)) and hands it to its DAO, so callers never pass `db` around.

Ref:
    1. https://stackoverflow.com/questions/62740603/how-can-i-implement-service-layer-in-django
    2. https://breadcrumbscollector.tech/how-to-implement-a-service-layer-in-django-rest-framework/
"""


class Service(ABC):
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.dao = self.dao_cls(db)

    @property
    @abstractmethod
    def dao_cls(self) -> Type[Dao]:
        """Return the DAO class associated with this service"""
        pass

    def __getattr__(self, name: str):
        """Fall through to the DAO for any method the service doesn't override itself"""
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.dao, name)


class ReadService(Service, ABC):
    """Base read-only service. Query methods (find_one, find_all, does_exist,
    get_count, get, all, ...) are inherited directly from the DAO via
    Service.__getattr__ - override here only when a method needs extra logic."""

    async def exists(self, filter_kwargs: Dict[str, Any]) -> bool:
        return await self.dao.does_exist(filter_kwargs)

    async def count(self, filter_kwargs: Optional[Dict[str, Any]] = None) -> int:
        return await self.dao.get_count(filter_kwargs)


class WriteService(Service, ABC):
    """Base write/mutation service.

    Every mutation takes `commit: bool = True`, passed straight through to
    the DAO: by default each call commits immediately (unchanged behavior
    for callers that make one write per request), but a subclass composing
    several writes into one business transaction can pass `commit=False` on
    all but the last call so they all land in a single commit."""

    async def create(self, data: DataInput, commit: bool = True) -> Optional[Base]:
        """Create a new object. Accepts a dict or a Pydantic schema."""
        return await self.dao.save(data, commit=commit)

    async def update(self, obj: Base, data: Optional[DataInput] = None, commit: bool = True) -> bool:
        """Update an existing object. Accepts a dict or a Pydantic schema."""
        if data:
            return await self.dao.partial_update(obj, data, commit=commit) is not None
        return await self.dao.update(obj, commit=commit)

    async def delete(self, obj: Base, commit: bool = True) -> bool:
        """Hard delete"""
        return await self.dao.delete(obj, commit=commit)

    async def soft_delete(self, obj: Base, commit: bool = True) -> bool:
        """Soft delete"""
        return await self.dao.soft_delete(obj, commit=commit)

    async def create_batch(self, objs: List[Base], commit: bool = True) -> bool:
        """Create multiple objects in bulk"""
        return await self.dao.save_batch(objs, commit=commit)

    async def update_batch(self, objs: List[Base], commit: bool = True) -> bool:
        """Update multiple objects"""
        return await self.dao.update_batch(objs, commit=commit)

    async def delete_batch(self, objs: List[Base], commit: bool = True) -> bool:
        """Delete multiple objects"""
        return await self.dao.delete_batch(objs, commit=commit)
