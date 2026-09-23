from typing import Any, Callable, List, Type, TypeVar, Union

from fastapi import Request
from pydantic import BaseModel

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
    def __init__(self) -> None:
        # Every core.db.get_db() generator opened by get_service() below,
        # so as_view()'s endpoint() can finish (and therefore close) each
        # one after the dispatched method returns - see as_view().
        self._db_generators: List[Any] = []

    async def get_service(self, service_cls: Type[ServiceT]) -> ServiceT:
        """Builds a Service the same way `Depends()` would in a normal
        function-based route, e.g. `await self.get_service(UserReadService)`.

        Needed because as_view() (see below) can't expose per-method
        `Depends()` parameters - it doesn't know in advance which method
        will run, so FastAPI never inspects get()'s/post()'s own signature
        to resolve them. This drives core.db.get_db()'s generator by hand
        to get the same AsyncSession a `Depends(get_db)` would have
        produced, and constructs the service with it directly."""
        db_gen = get_db()
        db = await anext(db_gen)
        self._db_generators.append(db_gen)
        return service_cls(db)

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
        # per-method params (path params, Depends()) here either - each
        # dispatched method only ever receives `request` (see module
        # docstring for what that costs on the request-body side; services
        # are built via self.get_service() instead of Depends()).
        async def endpoint(request: Request):
            action = request.method.lower()
            view = cls()
            method = getattr(view, action, None)
            if method is None:
                raise AttributeError(
                    f"{cls.__name__} has no method for HTTP verb {request.method!r} "
                    f"(expected an async def {action}(self, ...) on the class)."
                )
            try:
                return await method(request=request)
            finally:
                # get_service() drives core.db.get_db()'s generator by hand
                # (Depends() would normally do this); finish it here so its
                # `finally: await db.close()` still runs and the session
                # doesn't leak, mirroring what FastAPI's dependency-cleanup
                # does automatically for a Depends()-injected session.
                for db_gen in view._db_generators:
                    async for _ in db_gen:
                        pass

        return endpoint
