# syntax=docker/dockerfile:1
# =====================================================================================
# Tienda+ · API Gateway (Nginx)
#
# Imagen base: nginxinc/nginx-unprivileged:1.30-alpine
#   - Rama estable de Nginx (1.30.x). La etiqueta "1.30-alpine" se actualiza con cada
#     parche de seguridad de la rama: reconstruir la imagen recoge las correcciones.
#   - Variante "unprivileged": Nginx se ejecuta como usuario 101 (no root) y escucha en
#     8080, por lo que no necesita capacidades para abrir puertos < 1024.
#   - Alpine: imagen mínima (~20 MB) con muy pocos paquetes y menos superficie de ataque.
# No usa construcción multietapa porque no hay nada que compilar: solo se añade la
# configuración sobre la imagen oficial.
# =====================================================================================
FROM nginxinc/nginx-unprivileged:1.30-alpine

LABEL org.opencontainers.image.title="tienda-plus-gateway" \
      org.opencontainers.image.description="Tienda+ · API Gateway Nginx (equivalente local del Ingress de Azure)" \
      org.opencontainers.image.source="https://github.com/ricardoenriquezm95/proyecto-tienda-plus"

# La configuración pertenece a root y es de solo lectura para el proceso de Nginx.
COPY nginx.conf /etc/nginx/nginx.conf

USER 101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]

CMD ["nginx", "-g", "daemon off;"]
