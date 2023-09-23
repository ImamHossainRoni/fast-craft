from fastapi import FastAPI
from app.users.views import router as user_router
from config import settings

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.1")

app.include_router(user_router, prefix="/users", tags=['User'])
