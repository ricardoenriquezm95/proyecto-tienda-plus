
### 1. Descripción del dominio
---
#### Problema de negocio
Tienda+ es una pequeña tienda de productos locales, quiere vender por internet sin comprar ni mantener servidores propios. Sus ventas son muy irregulares: pocas ventas entre semanas y picos fuertes en épocas de campañas puntuales (Black Friday, navidad, rebajas). Con un servidor propio tendría que dimensionar para sus momentos pico y después pagar por los mismos servicios durante todo el año sin utilizar toda la capacidad comprada; con la nube paga solo por lo que usa y escala automáticamente en los picos.
El problema de negocio no es “gestionar productos de la tienda” sino más bien vender sin sobrevender: cuando hay muchos clientes y compran a la vez el mismo producto, el sistema debe garantizar que no se acepten pedidos sin stock real.

#### Lógica de negocio
-	Reserva de stock: al crear un pedido el servicio de orden de productos pide al servicio de catálogo de productos reservar las unidades. Si algún producto no tiene stock suficiente, el pedido se rechaza completo y se liberan las reservas de producto ya hechas.
-	Cálculo de pedido: Subtotal por línea y IVA 
-	Estados del pedido: se considerarán estos estados:
    -	PENDIENTE – PAGADO – ENVIADO.
    -	PENDIENTE – CANCELADO.
-	Cancelación con devolución de stock: Cancelar un pedido pendiente libera las unidades reservadas.
-	Pago simulado: El pago será simulado y no se integrará una pasarela real.

#### Casos de uso

| ID | ACTOR | CASO DE USO |
|----|---------|---------|
| C-001  | Cliente  | Consultar el catálogo y filtrar por categoría.    |
| C-002  | Cliente   | Ver el detalle y el stock de un producto.     |
| C-003  | Cliente | Crear un pedido con varios productos.    |
| C-004  | Cliente | Pagar un pedido(simulado).     |
| C-005  | Cliente | Cancelar un pedido pendiente.   |
| C-006  | Cliente | Consultar el estado de sus pedidos.     |
| C-007  | Administrador | Dar de alta productos y ajustar stock.     |
| C-008  | Administrador | Marcar un pedido pagado como enviado.     |

### 2.Justificación NIST SP 800-145
---
| Caracteristicas | Como lo aprovecha Tienda+ |
|----|---------|
| Autoservicio bajo demanda  | Todos los recursos se crean y destruyen sin intervención humana del proveedor, desde Terraform y GitHub Actions.  | 
| Acceso amplio a la red  | La API se expone por HTTPS en un endpoint público de Azure, accesible desde cualquier navegador, móvil o cliente HTTP mediante protocolos estándar.   |
| Asignación común de recursos  | Los contenedores se ejecutan sobre la infraestructura compartida de azure container Apps y la BD sobre un servicio gestionado por azure. | 
| Rápida elasticidad  | Container Apps escala cada microservicio de forma independiente según peticiones HTTP concurrentes maximo a 5 réplicas y vuelve a 0 cuando no hay tráfico. |
| Servicio medido  | Azure factura por segundos de vCPU / memoria y número de peticiones y por horas de cómputo y GB de almacenamiento. Azure monitor y cost management muestran el consumo real, lo que permite ajustar recursos y presupuestos. |

### 3.Mapeo de actores NIST SP 500-292
---
| Rol | Responsable | Responsabilidades |
|---|---|---|
| **Consumidor (Cloud Consumer)** | El desarrollador de TIENDA+ (en nombre del comercio). Los compradores, a su vez, consumen TIENDA+ como SaaS. | Contrata los servicios de Azure, acepta sus SLA, gestiona la suscripción y paga por uso. |
| **Proveedor (Cloud Provider)** | Microsoft Azure | Proporciona y opera la infraestructura física, la plataforma de contenedores, la base de datos y la facturación. |
| **Intermediario (Cloud Broker)** | GitHub Actions | Agregación: combina el repositorio, la integración continua, Container Registry y el despliegue en Azure en un único flujo automatizado. |
| **Auditor (Cloud Auditor)** | El profesorado | Evalúa de forma independiente la seguridad, el cumplimiento y el rendimiento mediante pruebas objetivas (repositorio, capturas, despliegue). |
| **Operador (Cloud Carrier)** | Los operadores de Internet y la red de Microsoft | Proporcionan la conectividad entre los compradores y Azure. |

#### Analisis de impacto economico
-   De Capex A Opex: No habría inversión inicial en servidores, licencias ni centro de datos; solo un gasto mensual variable ligado a las ventas.
-   Pago por uso y escalado a cero: Fuera de campaña, los servicios bajan a 0 réplicas y prácticamente no generan coste de cómputo.
-   Menos coste operativo: el proveedor asume parches, backups y hardware de la base de datos, por lo que no hace falta un administrador de sistemas dedicado.
-   Coste estimado: para un trafico bajo: Container Apps el cual contiene una cuota gratuita, una base de datos **Revisar azure pricing** 
-   Riesgo económico a vigilar: El escalado ilimitado puede disparar la factura; se fijaran un máximo de replicas y alertas de presupuesto en azure cost management.

### 4.Diagrama de arquitectura
---
#### Tecnologias a aplicar
| Elemento | Tecnología |
|---|---|
| Lenguaje / framework | Python 3.12 + FastAPI |
| Contenedores | Docker + Docker Compose (entorno local) |
| Cómputo en la nube | Azure Container Apps |
| Registro de imágenes | Azure Container Registry (ACR) |
| Persistencia | Azure SQL Database (SQL Server gestionado) — 1 base de datos por microservicio |
| Infraestructura como código  | Terraform |
| CI/CD  | GitHub Actions |
| Observabilidad  | Azure Monitor + Log Analytics |

---
![alt text](<Arquitectura cc.drawio.png>)

---
### 5.Especificación de API REST
---
##### Servicio "catalog-service"

| TIPO | RUTA | RESPUESTA | DESCRIPCIÓN | PAYLOADS |
|-------|-------|------------|-------------|----------|
| GET | `/api/v1/products/list` | 200 | Listar productos | `[{ "id": 1, "name": "Taza", "price": 12.5, "stock": 40 }]` |
| GET | `/api/v1/products/{id}` | 200, 404 | Detalle de un producto | `{ "id": 1, "name": "Taza", "price": 12.5, "stock": 40 }` |
| POST | `/api/v1/products/create` | 201, 422 | Crear producto (admin) | **Petición:** `{ "name": "Taza", "price": 12.5, "stock": 40 }`<br>**Respuesta:** `{ "id": 1, "name": "Taza", "price": 12.5, "stock": 40 }` |
| PATCH | `/api/v1/products/{id}/stock` | 200, 404 | Ajustar stock (admin) | **Petición:** `{ "delta": -5 }`<br>**Respuesta:** `{ "id": 1, "stock": 35 }` |
| POST | `/api/v1/products/{id}/reserve` | 200, 404, 409 | Reservar unidades (uso interno) | **Petición:** `{ "quantity": 2 }`<br>**Respuesta:** `{ "id": 1, "stock": 38 }` |
| POST | `/api/v1/products/{id}/release` | 200, 404 | Liberar unidades (uso interno) | **Petición:** `{ "quantity": 2 }`<br>**Respuesta:** `{ "id": 1, "stock": 40 }` |
| GET | `/health` | 200, 403 | Estado del servicio (admin) | `{ "status": "ok" }` |


#### Servicio "orders-service"

| Tipo | Ruta | Respuestas | Descripción | Payloads |
|------|------|------------|-------------|----------|
| POST | `/api/v1/orders/create` | 201, 409, 422 | Crear pedido | **Request:**<br>`{ "customer_email": "ana@example.com", "items": [{ "product_id": 1, "quantity": 2 }] }`<br><br>**Response 201:**<br>`{ "id": 101, "status": "PENDIENTE", "total": 30.25 }` |
| GET | `/api/v1/orders/{id}` | 200, 404 | Consultar pedido | `{ "id": 101, "customer_email": "ana@example.com", "items": [{ "product_id": 1, "quantity": 2 }], "status": "PENDIENTE", "total": 30.25 }` |
| GET | `/api/v1/orders?customer_email=` | 200 | Pedidos de un cliente | `[{ "id": 101, "status": "PENDIENTE", "total": 30.25 }]` |
| POST | `/api/v1/orders/{id}/pay` | 200, 404 | Pagar (simulado) | `{ "id": 101, "status": "PAGADO" }` |
| POST | `/api/v1/orders/{id}/cancel` | 200, 404, 409 | Cancelar y liberar stock | `{ "id": 101, "status": "CANCELADO" }` |
| POST | `/api/v1/orders/{id}/ship` | 200, 404, 409 | Marcar como enviado (admin) | `{ "id": 101, "status": "ENVIADO" }` |
| GET | `/health` | 200, 403 | Estado del servicio (admin) | `{ "status": "ok" }` |

#### Errores (todos los endpoints)
Los errores 404, 409, 422 y 403 usan el mismo formato:
`{ "detail": "Stock insuficiente" }`


