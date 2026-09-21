import uuid
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel
from sqlalchemy import Select, delete as sql_delete, func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Base

DataInput = Union[Dict[str, Any], BaseModel]


def _as_dict(data: DataInput) -> Dict[str, Any]:
    """Accept either a plain dict or a Pydantic schema, so callers never
    have to call .model_dump() themselves before handing data to the DAO."""
    if isinstance(data, BaseModel):
        return data.model_dump(exclude_unset=True)
    return data

"""
Module: base_dao.py
Author: Imam Hossain Roni

Description: Base DAO class for SQLAlchemy async models. Provides standard
CRUD operations, batch operations, soft-delete, and flexible query methods.
Each DAO instance is bound to one AsyncSession, passed in at construction.

Ref:
    1. https://en.wikipedia.org/wiki/Data_access_object
    2. https://hosseinnejati.medium.com/what-is-dao-understanding-the-data-access-object-pattern-6f5f7af77c36
"""


class Dao(ABC):
    SAVE_BATCH_SIZE = 1000

    def __init__(self, db: AsyncSession):
        self.db = db

    @property
    @abstractmethod
    def model_cls(self) -> Type[Base]:
        """Override in child DAO with the SQLAlchemy model class"""
        pass

    @cached_property
    def model(self) -> Type[Base]:
        """Cached access to model_cls"""
        return self.model_cls

    async def get(self, pk: uuid.UUID) -> Optional[Base]:
        if not pk:
            return None
        return await self.db.get(self.model, pk)

    def all(self, include_deleted: bool = False) -> Select:
        stmt = select(self.model)
        if hasattr(self.model, "deleted") and not include_deleted:
            stmt = stmt.where(self.model.deleted.is_(False))
        return stmt

    async def save(self, data: DataInput, commit: bool = True) -> Optional[Base]:
        """Insert one object. Accepts a dict or a Pydantic schema.

        Flushes (so the object gets its id and is visible to later queries
        in the same transaction) and only commits when `commit` is True -
        so a caller composing multiple writes into one business transaction
        can defer the commit until the last one."""
        if not data:
            return None
        obj = self.model(**_as_dict(data))
        self.db.add(obj)
        if commit:
            await self.db.commit()
            await self.db.refresh(obj)
        else:
            await self.db.flush()
        return obj

    async def save_batch(self, objs: List[Base], commit: bool = True) -> bool:
        """Insert multiple objects"""
        if not objs:
            return False
        self.db.add_all(objs)
        await self.db.commit() if commit else await self.db.flush()
        return True

    async def update(self, obj: Optional[Base], commit: bool = True) -> bool:
        if not obj:
            return False
        self.db.add(obj)
        await self.db.commit() if commit else await self.db.flush()
        return True

    async def update_batch(self, objs: List[Base], commit: bool = True) -> bool:
        if not objs:
            return False
        try:
            self.db.add_all(objs)
            await self.db.commit() if commit else await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def update_batch_by_query(
        self,
        query_kwargs: Dict[str, Any],
        new_kwargs: Dict[str, Any],
    ) -> bool:
        if not query_kwargs or not new_kwargs:
            return False

        stmt = sql_update(self.model).filter_by(**query_kwargs).values(**new_kwargs)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def partial_update(self, obj: Base, update_fields: DataInput, commit: bool = True) -> Optional[Base]:
        if not obj or not update_fields:
            return None

        if not isinstance(obj, self.model_cls):
            raise ValueError(f"Object must be instance of {self.model_cls.__name__}")

        for field, value in _as_dict(update_fields).items():
            if not hasattr(obj, field):
                raise ValueError(f"Field '{field}' does not exist on {self.model_cls.__name__}")
            setattr(obj, field, value)

        success = await self.update(obj, commit=commit)
        if success:
            await self.db.refresh(obj)
            return obj
        return None

    async def delete(self, obj: Optional[Base], commit: bool = True) -> bool:
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit() if commit else await self.db.flush()
        return True

    async def delete_batch(self, objs: List[Base], commit: bool = True) -> bool:
        if not objs:
            return False
        for obj in objs:
            await self.db.delete(obj)
        await self.db.commit() if commit else await self.db.flush()
        return True

    async def delete_batch_by_query(self, filter_kwargs: Dict[str, Any]) -> bool:
        stmt = sql_delete(self.model).filter_by(**filter_kwargs)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def soft_delete(self, obj: Optional[Base], commit: bool = True) -> bool:
        """Soft-delete (requires model to have a 'deleted' boolean field)"""
        if not obj or not hasattr(obj, "deleted"):
            return False
        obj.deleted = True
        return await self.update(obj, commit=commit)

    async def find_one(
        self,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        order_bys: Optional[List[Any]] = None,
    ) -> Optional[Base]:
        stmt = select(self.model)
        if filter_kwargs:
            stmt = stmt.filter_by(**filter_kwargs)
        if order_bys:
            stmt = stmt.order_by(*order_bys)
        result = await self.db.execute(stmt.limit(1))
        return result.scalars().first()

    def query(
        self,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        order_bys: Optional[List[Any]] = None,
    ) -> Select:
        stmt = select(self.model)
        if filter_kwargs:
            stmt = stmt.filter_by(**filter_kwargs)
        if order_bys:
            stmt = stmt.order_by(*order_bys)
        return stmt

    async def find_all(
        self,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        order_bys: Optional[List[Any]] = None,
    ) -> List[Base]:
        result = await self.db.execute(self.query(filter_kwargs, order_bys))
        return list(result.scalars().all())

    async def does_exist(self, filter_kwargs: Dict[str, Any]) -> bool:
        stmt = select(self.model.id).filter_by(**filter_kwargs).limit(1)
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def get_count(self, filter_kwargs: Optional[Dict[str, Any]] = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        if filter_kwargs:
            stmt = stmt.filter_by(**filter_kwargs)
        result = await self.db.execute(stmt)
        return result.scalar_one()
