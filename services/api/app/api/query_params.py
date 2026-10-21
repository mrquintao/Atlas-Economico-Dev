"""Reject query parameters that the matched route does not declare (or repeats it does not allow).

Without this, a typo such as ``?start=2030-01-01`` (instead of ``start_date``) is silently ignored
and the API answers with the whole series, which looks like a valid filtered response. Likewise,
``?start_date=a&start_date=b`` silently used the last value.
"""

from collections.abc import Sequence
from types import UnionType
from typing import Any, Union, get_args, get_origin

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.api.errors import ApiError

_SEQUENCE_ORIGINS = (list, tuple, set, frozenset, Sequence)


def _unwrap_optional(annotation: Any) -> Any:
    """``X | None`` → ``X`` (other unions are kept as they are)."""
    if get_origin(annotation) in (Union, UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _is_sequence(annotation: Any) -> bool:
    origin = get_origin(_unwrap_optional(annotation))
    return origin is not None and isinstance(origin, type) and issubclass(origin, _SEQUENCE_ORIGINS)


def _declared_query_params(route: APIRoute) -> dict[str, bool]:
    """Query parameter names of the route and its (sub)dependencies → whether they may repeat.

    Pydantic models declared as query parameters (``Annotated[Model, Query()]``) contribute
    their fields.
    """
    declared: dict[str, bool] = {}
    pending: list[Dependant] = [route.dependant]
    while pending:
        dependant = pending.pop()
        for param in dependant.query_params:
            annotation = _unwrap_optional(param.field_info.annotation)
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                for name, field in annotation.model_fields.items():
                    # The name actually read from the query string: validation alias, alias, name.
                    query_name = (
                        field.validation_alias
                        if isinstance(field.validation_alias, str)
                        else field.alias or name
                    )
                    declared[query_name] = _is_sequence(field.annotation)
            else:
                declared[param.alias] = _is_sequence(annotation)
        pending.extend(dependant.dependencies)
    return declared


def _names(names: list[str]) -> str:
    return ", ".join(name if name else '""' for name in names)


def reject_unknown_query_params(request: Request) -> None:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return
    declared = _declared_query_params(route)
    unknown = sorted(set(request.query_params) - set(declared))
    if unknown:
        raise ApiError(
            422,
            "unknown_parameter",
            f"Parâmetro(s) de consulta desconhecido(s): {_names(unknown)}.",
            {"unknown": unknown, "allowed": sorted(declared)},
        )
    repeated = sorted(
        name
        for name, may_repeat in declared.items()
        if not may_repeat and len(request.query_params.getlist(name)) > 1
    )
    if repeated:
        raise ApiError(
            422,
            "repeated_parameter",
            f"Parâmetro(s) informado(s) mais de uma vez: {_names(repeated)}.",
            {"repeated": repeated},
        )
