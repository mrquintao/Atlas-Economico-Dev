"""Reject query parameters that the matched route does not declare.

Without this, a typo such as ``?start=2030-01-01`` (instead of ``start_date``) is silently ignored
and the API answers with the whole series, which looks like a valid filtered response.
"""

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api.errors import ApiError


def _declared_query_params(route: APIRoute) -> set[str]:
    """Aliases of the query parameters of the route and of all its (sub)dependencies."""
    names: set[str] = set()
    pending: list[Dependant] = [route.dependant]
    while pending:
        dependant = pending.pop()
        names.update(param.alias for param in dependant.query_params)
        pending.extend(dependant.dependencies)
    return names


def reject_unknown_query_params(request: Request) -> None:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return
    unknown = sorted(set(request.query_params) - _declared_query_params(route))
    if unknown:
        raise ApiError(
            422,
            "unknown_parameter",
            f"Parâmetro(s) de consulta desconhecido(s): {', '.join(unknown)}.",
            {"unknown": unknown, "allowed": sorted(_declared_query_params(route))},
        )
