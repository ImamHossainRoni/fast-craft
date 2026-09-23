"""
Module: urls.py

Description: Root URL configuration. Every app's router is wired in here,
    Django-style, instead of in main.py. To add a new app, import its
    router and register it below.
"""
from fastapi import status
from fastapi import APIRouter
from apps.users.urls import router as user_router
from config import settings

NOT_FOUND_RESPONSE = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}}

router = APIRouter(prefix=settings.API_V1_PREFIX)

router.include_router(user_router, prefix="/users", tags=["User"], responses=NOT_FOUND_RESPONSE)
