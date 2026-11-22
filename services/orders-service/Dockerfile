# syntax=docker/dockerfile:1
# =====================================================================================
# Tienda+ · orders-service · imagen de producción
#
# Imagen base: python:3.12-slim-bookworm
#   - Misma versión de Python que el proyecto (3.12) y que la CI.
#   - "slim" (~45 MB comprimida) elimina compiladores, documentación y paquetes
#     innecesarios de la imagen completa (~350 MB), reduciendo superficie de ataque.
#   - Basada en glibc: compatible con las ruedas manylinux de pymssql, uvloop o
#     pydantic-core; Alpine (musl) obligaría a compilarlas y no reduce el tamaño final.
#   - Distroless se descartó porque su Python (3.11) no coincide con el del proyecto.
# =====================================================================================

# ---------- Etapa 1: builder (instala dependencias en un entorno virtual aislado) -----
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build
# Se copia SOLO requirements.txt: esta capa (la más lenta) queda en caché mientras
# no cambien las dependencias, aunque cambie el código fuente.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Etapa 2: runtime (solo lo necesario para ejecutar) ------------------------
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="tienda-plus-orders-service" \
      org.opencontainers.image.description="Tienda+ · pedidos con reserva de stock y cálculo de IVA" \
      org.opencontainers.image.source="https://github.com/ricardoenriquezm95/proyecto-tienda-plus"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Usuario y grupo sin privilegios, sin shell de login ni directorio home.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# El entorno virtual y el código pertenecen a root y son de solo lectura para "app":
# el proceso no puede modificar su propio código (inmutabilidad).
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER 10001:10001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health/live', timeout=3).status == 200 else 1)"]

# Forma exec: uvicorn es el PID 1 y recibe directamente SIGTERM (parada ordenada).
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
