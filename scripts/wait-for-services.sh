set -euo pipefail
TIMEOUT="${1:-300}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"

deadline=$(( $(date +%s) + TIMEOUT ))
until curl -fsS "$GATEWAY_URL/healthz" >/dev/null 2>&1 \
   && curl -fsS "$GATEWAY_URL/catalog/health/live" >/dev/null 2>&1 \
   && curl -fsS "$GATEWAY_URL/orders/health/live" >/dev/null 2>&1; do
  if (( $(date +%s) > deadline )); then
    echo "Los servicios no respondieron en ${TIMEOUT}s" >&2
    docker compose ps -a
    exit 1
  fi
  echo "Esperando a los servicios..."
  sleep 5
done
echo "gateway, catalog-service y orders-service listos"
