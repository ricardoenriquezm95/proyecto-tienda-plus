"""Control de acceso mínimo para operaciones de administración (``X-Admin-Token``)."""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status


def require_admin(request: Request, x_admin_token: Annotated[str | None, Header()] = None) -> None:
    expected: str = request.app.state.settings.admin_token
    if not x_admin_token or not secrets.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido a administradores"
        )
