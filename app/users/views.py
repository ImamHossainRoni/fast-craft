from fastapi import Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.users.schemas import UserBase
from core.db import get_db

router = APIRouter()


@router.post('/')
async def create_user(user: UserBase, db: AsyncSession = Depends(get_db)):
    db_user = User(username=user.username)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get('/')
async def get_users(db: AsyncSession = Depends(get_db)):
    results = await db.execute(select(User))
    users = results.scalars().all()
    return {"users": users}
