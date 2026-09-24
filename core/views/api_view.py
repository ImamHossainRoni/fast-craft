from typing import Callable, Type, TypeVar, Union, Any, List

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db

ServiceT = TypeVar("ServiceT")

"""
Module: api_view.py
Author: Imam Hossain Roni

Description: DRF-style class-based view. Subclasses define instance
methods (get, post, ...) that use `self` freely, same look as Django REST
Framework's APIView.

DRF's real APIView has ONE as_view() per class; dispatch to get()/post()/...
happens inside, at request time, by reading the HTTP method off the
request. This class does the same:

    router.add_api_route("/login", LoginAPIView.as_view(), methods=["GET", "POST"])

`as_view()` takes no argument - the HTTP verb is read from `request.method`
each time a request actually arrives, and dispatched to the same-named
method on a fresh view instance.

Trade-off, stated plainly: because as_view() no longer knows in advance
which single method (get/post/put/...) a given call will run, it can't
copy that ONE method's parameter signature onto the route the way a
per-method as_view("post") could - so FastAPI can no longer auto-parse and
auto-validate a request body from a typed parameter like
`user_data: UserCreationSchema`. Any method that needs the body (POST,
PUT, PATCH) must read and validate it itself, e.g.:

    async def post(self, request: Request, service: UserWriteService = Depends()):
        user_data = UserCreationSchema.model_validate(await request.json())
        ...

This is the cost of one as_view() call covering every verb instead of one
per verb; it is not a limitation of this implementation, it's inherent to
FastAPI deciding how to parse a request from the signature it inspected
at route-registration time, before request.method is known.
"""


class APIView:
    def __init__(self, db: AsyncSession) -> None:
        # `db` is resolved by FastAPI's real Depends(get_db) in as_view()'s
        # endpoint() below, not driven by hand - FastAPI owns the get_db()
        # generator's lifecycle (including closing it) the same way it
        # would for any normal Depends()-based route.
        self._db = db

    async def get_service(self, service_cls: Type[ServiceT]) -> ServiceT:
        """Builds a Service from the AsyncSession FastAPI already injected
        into this view via Depends(get_db), e.g.
        `await self.get_service(UserReadService)`.

        Needed because as_view() (see below) can't expose per-method
        `Depends()` parameters - it doesn't know in advance which method
        will run, so FastAPI never inspects get()'s/post()'s own signature
        to resolve them. The session itself is still real DI; only the
        per-method service construction is done by hand."""
        return service_cls(self._db)

    def serialize(self, obj: Union[Any, List[Any]], schema: Type[BaseModel]):
        """schema.model_validate applied to one object or a list of objects,
        mirroring DRF's serializer_class(obj, many=True).data.

        `schema` is passed explicitly at each call site, e.g.:

            return Response(self.serialize(users, UserResponseSchema), ...)

        DRF-style: same as instantiating a different Serializer inline per
        method (e.g. `TokenSerializer(tokens).data`) instead of relying on
        one `self.serializer_class` shared across every method - a method
        whose output doesn't match another method's shape just names its
        own schema where it's used, no shared class attribute required."""
        if isinstance(obj, (list, tuple)):
            return [schema.model_validate(item) for item in obj]
        return schema.model_validate(obj)

    @classmethod
    def as_view(cls) -> Callable:
        # No **kwargs here: FastAPI inspects this exact signature to build
        # the route, and a bare **kwargs would show up as a literal required
        # "kwargs" field instead of being passed through. Since as_view()
        # doesn't know in advance which method will run, it can't expose
        # per-method params (path params, per-method Depends()) here - each
        # dispatched method only ever receives `request` (see module
        # docstring for what that costs on the request-body side; services
        # are built via self.get_service() from the one `db` below instead
        # of their own Depends()).
        #
        # `db` IS real Depends(get_db) though: it's a class-level (not
        # per-method) dependency, so FastAPI can see and resolve it here,
        # and it owns get_db()'s generator lifecycle - including closing it
        # - exactly as it would for a normal Depends()-injected session.
        async def endpoint(request: Request, db: AsyncSession = Depends(get_db)):
            action = request.method.lower()
            view = cls(db)
            method = getattr(view, action, None)
            if method is None:
                raise AttributeError(
                    f"{cls.__name__} has no method for HTTP verb {request.method!r} "
                    f"(expected an async def {action}(self, ...) on the class)."
                )
            return await method(request=request)

        return endpoint
