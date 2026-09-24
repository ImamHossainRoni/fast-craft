from fastapi import FastAPI
from config import settings
from urls import router

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.1")

app.include_router(router)
