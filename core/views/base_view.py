import inspect
from functools import wraps
from typing import Any, Callable, List, NoReturn, Optional, Type, Union

from fastapi import HTTPException, status
from pydantic import BaseModel

from core.response import BaseResponse

"""
Module: base_view.py
Author: Imam Hossain Roni

Description: Base class for class-based views, Django-style: one small
class, one action, one `as_view()` - no method-name/verb argument needed,
because there's only ever one action method to find:

    class UserListView(BaseView):
        async def get(self, service: UserReadService = Depends()):
            ...

    router.add_api_route("/", UserListView.as_view(), methods=[HTTP.GET])

`as_view()` finds that one action method by taking whichever method the
subclass defines beyond BaseView itself (there must be exactly one),
builds a fresh instance per request (mirroring Django, which also
instantiates its view once per request), and exposes that method's own
signature (with `self` dropped) to FastAPI - so per-view `Depends()`
resolves normally. This is different from core/views/api_view.py's
APIView.as_view() (kept only for core/management/commands/startapp.py's
older scaffold), which dispatches every HTTP verb through one shared
function and can't expose any single method's real signature to FastAPI.
"""


class BaseView:
    @classmethod
    def as_view(cls) -> Callable:
        own_methods = [
            name
            for name, value in vars(cls).items()
            if not name.startswith("_") and inspect.iscoroutinefunction(value)
        ]
        if len(own_methods) != 1:
            raise TypeError(
                f"{cls.__name__} must define exactly one action method to use as_view() "
                f"with no argument; found {own_methods or 'none'}."
            )
        method_name = own_methods[0]
        unbound = getattr(cls, method_name)
        sig = inspect.signature(unbound)
        params = list(sig.parameters.values())[1:]  # drop `self`

        @wraps(unbound)
        async def view(*args, **kwargs):
            instance = cls()
            bound = getattr(instance, method_name)
            return await bound(*args, **kwargs)

        view.__signature__ = sig.replace(parameters=params)
        return view

    @staticmethod
    def respond(code: int = status.HTTP_200_OK, msg: str = "", data: Optional[Any] = None) -> BaseResponse:
        return BaseResponse(code=code, msg=msg, data=data)

    @staticmethod
    def handle_error(err: Exception) -> NoReturn:
        raise HTTPException(
            status_code=getattr(err, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=getattr(err, "detail", str(err)),
        )

    @staticmethod
    def serialize(obj: Union[Any, List[Any]], schema: Type[BaseModel]):
        """schema.model_validate applied to one object or a list of objects,
        mirroring DRF's serializer_class(obj, many=True).data."""
        if isinstance(obj, (list, tuple)):
            return [schema.model_validate(item) for item in obj]
        return schema.model_validate(obj)
