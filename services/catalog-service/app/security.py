"""Control de acceso mínimo basado en tokens compartidos.

- ``X-Admin-Token``: operaciones de administración (alta de productos, stock, /health).
- ``X-Internal-Token``: llamadas servicio a servicio (reserve / release desde orders-service).
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status


def _check_token(provided: str | None, expected: str, message: str) -> None:
    # compare_digest evita ataques de temporización al comparar secretos.
    if not provided or not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def require_admin(request: Request, x_admin_token: Annotated[str | None, Header()] = None) -> None:
    _check_token(
        x_admin_token,
        request.app.state.settings.admin_token,
        "Acceso restringido a administradores",
    )


def require_internal(
    request: Request, x_internal_token: Annotated[str | None, Header()] = None
) -> None:
    _check_token(
        x_internal_token,
        request.app.state.settings.internal_token,
        "Operación reservada a servicios internos",
    )
