#! python
# -*- coding: utf-8 -*-

"""
Module: config.py
Author: Imam Hossain Roni
Created: September 20, 2023

Description: ''
"""
import os
from pydantic_settings import BaseSettings
from decouple import config


class Settings(BaseSettings):
    """
    Settings class for FastCraft: FastAPI Based Backend Starter Kit.

    This class defines configuration settings for the FastCraft project.
    It uses Pydantic for setting validation and loading from environment variables
    using 'decouple' for sensitive data.

    Attributes:
        PROJECT_NAME (str): The name of the FastCraft project.
        BASE_DIR (str): The base directory of the project.
        API_V1_PREFIX (str): The API version 1 prefix.
        SECRET_KEY (str): The secret key for cryptographic operations.
        JWT_ALGORITHM (str): The algorithm used for JWT tokens.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Expiration time for access tokens in minutes.
        REFRESH_TOKEN_EXPIRE_DAYS (int): Expiration time for refresh tokens in days.
        ... More...

    Config:
        case_sensitive (bool): If True, settings are case-sensitive.

    """
    PROJECT_NAME: str = "FastCraft: FastAPI Based Backend Starter Kit"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = config("SECRET_KEY")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS")

    class Config:
        case_sensitive = True


settings = Settings()
