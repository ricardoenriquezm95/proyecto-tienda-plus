
## 1. Descripción del dominio
### Problema de negocio
Tienda+ es una pequeña tienda de productos locales, quiere vender por internet sin comprar ni mantener servidores propios. Sus ventas son muy irregulares: pocas ventas entre semanas y picos fuertes en épocas de campañas puntuales (Black Friday, navidad, rebajas). Con un servidor propio tendría que dimensionar para sus momentos pico y después pagar por los mismos servicios durante todo el año sin utilizar toda la capacidad comprada; con la nube paga solo por lo que usa y escala automáticamente en los picos.
El problema de negocio no es “gestionar productos de la tienda” sino más bien vender sin sobrevender: cuando hay muchos clientes y compran a la vez el mismo producto, el sistema debe garantizar que no se acepten pedidos sin stock real.

### Lógica de negocio
-	Reserva de stock: al crear un pedido el servicio de orden de productos pide al servicio de catálogo de productos reservar las unidades. Si algún producto no tiene stock suficiente, el pedido se rechaza completo y se liberan las reservas de producto ya hechas.
-	Cálculo de pedido: Subtotal por línea y IVA 
-	Estados del pedido: se considerarán estos estados:
    -	PENDIENTE – PAGADO – ENVIADO.
    -	PENDIENTE – CANCELADO.
-	Cancelación con devolución de stock: Cancelar un pedido pendiente libera las unidades reservadas.
-	Pago simulado: El pago será simulado y no se integrará una pasarela real.

### Casos de uso

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

## 2.Justificación NIST SP 800-145

| Caracteristicas | Como lo aprovecha Tienda+ |
|----|---------|
| Autoservicio bajo demanda  | Todos los recursos se crean y destruyen sin intervención humana del proveedor, desde Terraform y GitHub Actions. Crear un entorno de pruebas es ejecutar Terraform.  | 
| Acceso amplio a la red  | La API se expone por HTTPS en un endpoint público de Azure, accesible desde cualquier navegador, móvil o cliente HTTP mediante protocolos estándar.   |
| Asignación común de recursos  | Los contenedores se ejecutan sobre la infraestructura compartida de azure container Apps y la BD sobre un servicio gestionado por azure. | 
| Rápida elasticidad  | Container Apps escala cada microservicio de forma independiente según peticiones HTTP concurrentes maximo a 5 réplicas y vuelve a 0 cuando no hay tráfico. |
| Servicio medido  | Azure factura por segundos de vCPU / memoria y número de peticiones y por horas de cómputo y GB de almacenamiento. Azure monitor y cost management muestran el consumo real, lo que permite ajustar recursos y presupuestos. |




