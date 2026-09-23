from http import HTTPMethod

"""
Module: http.py

Description: Re-exports the stdlib HTTPMethod enum (a StrEnum: HTTPMethod.GET
== "GET") so call sites can write HTTP.GET/HTTP.POST instead of raw strings,
e.g.:

    router.add_api_route("/users/", UsersListAPIView.as_view(), methods=[HTTP.GET, HTTP.POST])

Because it's a StrEnum, it drops into methods=[...] and any other
string-typed FastAPI/Starlette parameter with no conversion needed.
"""

HTTP = HTTPMethod

__all__ = ["HTTP"]
