from typing import Any, Generic, Optional, TypeVar

from fastapi import status as http_status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

"""
Module: response.py
Author: Imam Hossain Roni

Description: Standard response envelope returned by views, mirroring DRF's
Response - a consistent {code, msg, data} shape for every endpoint.
"""

DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    code: int
    msg: str = ""
    data: Optional[Any] = None


def Response(data: Any = None, status: int = http_status.HTTP_200_OK, msg: str = "") -> JSONResponse:
    envelope = BaseResponse(code=status, msg=msg, data=data)
    return JSONResponse(status_code=status, content=jsonable_encoder(envelope))