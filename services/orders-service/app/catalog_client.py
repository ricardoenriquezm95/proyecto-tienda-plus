"""Cliente HTTP del catalog-service (comunicación REST interna)."""

from __future__ import annotations

from typing import Any

import httpx


class CatalogError(Exception):
    """Base de los errores al hablar con el catálogo."""


class ProductNotFoundError(CatalogError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El producto {product_id} no existe")
        self.product_id = product_id


class InsufficientStockError(CatalogError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"Stock insuficiente para el producto {product_id}")
        self.product_id = product_id


class CatalogUnavailableError(CatalogError):
    pass


class CatalogClient:
    def __init__(
        self,
        base_url: str,
        internal_token: str,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"X-Internal-Token": internal_token, "Accept": "application/json"},
            # Reintenta errores de conexión (no peticiones ya procesadas).
            transport=transport or httpx.HTTPTransport(retries=2),
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise CatalogUnavailableError(f"catalog-service no responde: {exc}") from exc

    @staticmethod
    def _raise_unexpected(response: httpx.Response) -> None:
        if response.is_error:
            raise CatalogUnavailableError(
                f"Respuesta inesperada del catálogo: HTTP {response.status_code}"
            )

    def get_product(self, product_id: int) -> dict[str, Any]:
        response = self._request("GET", f"/api/v1/products/{product_id}")
        if response.status_code == httpx.codes.NOT_FOUND:
            raise ProductNotFoundError(product_id)
        self._raise_unexpected(response)
        return response.json()

    def reserve(self, product_id: int, quantity: int) -> int:
        response = self._request(
            "POST", f"/api/v1/products/{product_id}/reserve", json={"quantity": quantity}
        )
        if response.status_code == httpx.codes.NOT_FOUND:
            raise ProductNotFoundError(product_id)
        if response.status_code == httpx.codes.CONFLICT:
            raise InsufficientStockError(product_id)
        self._raise_unexpected(response)
        return response.json()["stock"]

    def release(self, product_id: int, quantity: int) -> int:
        response = self._request(
            "POST", f"/api/v1/products/{product_id}/release", json={"quantity": quantity}
        )
        if response.status_code == httpx.codes.NOT_FOUND:
            raise ProductNotFoundError(product_id)
        self._raise_unexpected(response)
        return response.json()["stock"]
