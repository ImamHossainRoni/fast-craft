from typing import Any, NoReturn, Optional

from fastapi import HTTPException, status

from core.response import BaseResponse

"""
Module: base_view.py
Author: Imam Hossain Roni

Description: Base class for class-based views. Each endpoint is a
`@staticmethod` on the subclass (so FastAPI can still inspect its own
signature for Depends()/body parsing) that calls BaseView.respond /
BaseView.handle_error instead of repeating the same try/except and
BaseResponse construction everywhere.
"""


class BaseView:
    @staticmethod
    def respond(code: int = status.HTTP_200_OK, msg: str = "", data: Optional[Any] = None) -> BaseResponse:
        return BaseResponse(code=code, msg=msg, data=data)

    @staticmethod
    def handle_error(err: Exception) -> NoReturn:
        raise HTTPException(
            status_code=getattr(err, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=getattr(err, "detail", str(err)),
        )
